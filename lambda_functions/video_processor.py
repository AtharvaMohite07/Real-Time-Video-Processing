import json
import boto3
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
kinesis_client = boto3.client('kinesis')

def lambda_handler(event, context):
    """
    AWS Lambda function for serverless video processing
    Processes video frames uploaded to S3 and performs real-time analytics
    """
    try:
        # Parse the event
        if 'Records' in event:
            # S3 trigger event
            return process_s3_event(event, context)
        elif 'frame_data' in event:
            # Direct API call with frame data
            return process_frame_data(event, context)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event format'})
            }
    
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def process_s3_event(event, context):
    """Process video file uploaded to S3"""
    results = []
    
    for record in event['Records']:
        # Get S3 bucket and key
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        logger.info(f"Processing video: s3://{bucket}/{key}")
        
        # Download video file
        try:
            local_path = f'/tmp/{key.split("/")[-1]}'
            s3_client.download_file(bucket, key, local_path)
            
            # Process video
            video_results = process_video_file(local_path)
            
            # Save results back to S3
            output_key = f"processed/{key.replace('.mp4', '_analysis.json').replace('.avi', '_analysis.json')}"
            s3_client.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=json.dumps(video_results, indent=2),
                ContentType='application/json'
            )
            
            results.append({
                'input_video': key,
                'output_analysis': output_key,
                'frames_processed': video_results['total_frames'],
                'processing_time': video_results['total_processing_time'],
                'objects_detected': video_results['total_objects_detected']
            })
            
        except Exception as e:
            logger.error(f"Error processing {key}: {str(e)}")
            results.append({
                'input_video': key,
                'error': str(e)
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Video processing completed',
            'results': results
        })
    }

def process_frame_data(event, context):
    """Process single frame data sent directly to Lambda"""
    try:
        # Decode base64 frame data
        frame_data = event['frame_data']
        image_bytes = base64.b64decode(frame_data)
        
        # Convert to OpenCV format
        image = Image.open(BytesIO(image_bytes))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Process frame
        analysis_result = analyze_frame(frame)
        
        # Send to Kinesis for real-time streaming
        if event.get('stream_name'):
            send_to_kinesis(analysis_result, event['stream_name'])
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'analysis': analysis_result,
                'processing_time': analysis_result['processing_time']
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing frame: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def process_video_file(video_path):
    """Process entire video file and return comprehensive analysis"""
    cap = cv2.VideoCapture(video_path)
    
    # Initialize results
    results = {
        'video_path': video_path,
        'total_frames': 0,
        'total_processing_time': 0,
        'frames_analysis': [],
        'summary': {
            'total_objects_detected': 0,
            'total_faces_detected': 0,
            'average_quality_score': 0,
            'motion_events': 0
        }
    }
    
    frame_count = 0
    total_quality = 0
    start_time = time.time()
    
    # Process every 30th frame (1 second intervals for 30fps video)
    frame_skip = 30
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Skip frames for performance
        if frame_count % frame_skip != 0:
            continue
        
        # Analyze frame
        frame_analysis = analyze_frame(frame)
        
        # Update summary
        results['summary']['total_objects_detected'] += len(frame_analysis.get('objects', []))
        results['summary']['total_faces_detected'] += len(frame_analysis.get('faces', []))
        
        quality_score = frame_analysis.get('quality_score', 0)
        total_quality += quality_score
        
        if frame_analysis.get('motion_detected', False):
            results['summary']['motion_events'] += 1
        
        # Store frame analysis (limit to key frames only)
        if len(results['frames_analysis']) < 100:  # Limit storage
            results['frames_analysis'].append({
                'frame_number': frame_count,
                'timestamp': frame_count / 30.0,  # Assuming 30fps
                'quality_score': quality_score,
                'objects_count': len(frame_analysis.get('objects', [])),
                'faces_count': len(frame_analysis.get('faces', []))
            })
    
    cap.release()
    
    # Finalize results
    processed_frames = len(results['frames_analysis'])
    results['total_frames'] = frame_count
    results['total_processing_time'] = time.time() - start_time
    results['summary']['average_quality_score'] = total_quality / max(processed_frames, 1)
    results['summary']['frames_processed'] = processed_frames
    
    return results

def analyze_frame(frame):
    """Analyze a single frame using OpenCV"""
    start_time = time.time()
    
    # Basic frame info
    height, width = frame.shape[:2]
    
    # Initialize results
    analysis = {
        'timestamp': time.time(),
        'frame_size': [width, height],
        'objects': [],
        'faces': [],
        'motion_detected': False,
        'quality_score': 0,
        'color_analysis': {},
        'processing_time': 0
    }
    
    try:
        # Face detection using OpenCV
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in faces:
            analysis['faces'].append({
                'bbox': [int(x), int(y), int(w), int(h)],
                'confidence': 0.8,  # OpenCV doesn't provide confidence
                'area': int(w * h)
            })
        
        # Simple edge-based object detection
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # Filter small objects
                x, y, w, h = cv2.boundingRect(contour)
                analysis['objects'].append({
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'area': int(area),
                    'type': 'detected_object'
                })
        
        # Color analysis
        mean_color = np.mean(frame, axis=(0, 1))
        analysis['color_analysis'] = {
            'mean_color': [int(c) for c in mean_color],
            'brightness': float(np.mean(gray))
        }
        
        # Quality score calculation
        analysis['quality_score'] = calculate_quality_score(analysis)
        
        # Motion detection (simplified)
        analysis['motion_detected'] = len(analysis['objects']) > 5
        
    except Exception as e:
        logger.warning(f"Error in frame analysis: {str(e)}")
    
    analysis['processing_time'] = time.time() - start_time
    return analysis

def calculate_quality_score(analysis):
    """Calculate quality score for a frame"""
    score = 0
    
    # Face detection score (0-40)
    faces_count = len(analysis['faces'])
    if faces_count > 0:
        score += min(faces_count * 20, 40)
    
    # Object detection score (0-30)
    objects_count = len(analysis['objects'])
    if objects_count > 0:
        score += min(objects_count * 5, 30)
    
    # Brightness score (0-30)
    brightness = analysis['color_analysis'].get('brightness', 0)
    if 50 < brightness < 200:  # Good brightness range
        score += 30
    elif brightness > 0:
        score += 15
    
    return min(score, 100)

def send_to_kinesis(data, stream_name):
    """Send analysis results to Kinesis stream"""
    try:
        response = kinesis_client.put_record(
            StreamName=stream_name,
            Data=json.dumps(data),
            PartitionKey=str(data.get('timestamp', time.time()))
        )
        logger.info(f"Data sent to Kinesis stream {stream_name}: {response['SequenceNumber']}")
    except Exception as e:
        logger.error(f"Error sending to Kinesis: {str(e)}")

# For testing locally
if __name__ == "__main__":
    # Test event
    test_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test-video.mp4"}
                }
            }
        ]
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
