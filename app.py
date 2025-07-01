import cv2
import numpy as np
from flask import Flask, render_template, Response, request, jsonify
from flask_cors import CORS
import threading
import queue
import time
import json
import os
import sys
from datetime import datetime
import base64
import io
from PIL import Image
import boto3
from botocore.exceptions import ClientError
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our advanced processor
try:
    from advanced_analyzer import AdvancedVideoProcessor
    ADVANCED_PROCESSOR_AVAILABLE = True
except ImportError:
    ADVANCED_PROCESSOR_AVAILABLE = False
    logging.warning("Advanced processor not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class VideoProcessor:
    def __init__(self):
        self.cap = None
        self.processing_enabled = False
        
        # Initialize advanced processor if available
        if ADVANCED_PROCESSOR_AVAILABLE:
            self.advanced_processor = AdvancedVideoProcessor()
            logger.info("Advanced video processor initialized")
        else:
            self.advanced_processor = None
            
        # Basic cascades for fallback - with proper error handling
        try:
            # Try new OpenCV path first
            cascade_path = cv2.data.haarcascades if hasattr(cv2, 'data') else cv2.__file__.replace('__init__.py', 'data/')
            self.face_cascade = cv2.CascadeClassifier(cascade_path + 'haarcascade_frontalface_default.xml')
            self.eye_cascade = cv2.CascadeClassifier(cascade_path + 'haarcascade_eye.xml')
            self.body_cascade = cv2.CascadeClassifier(cascade_path + 'haarcascade_fullbody.xml')
        except Exception as e:
            logger.warning(f"Failed to load OpenCV cascades: {e}. Some detection features may not work.")
            self.face_cascade = None
            self.eye_cascade = None
            self.body_cascade = None
        
        # Video processing options
        self.processing_options = {
            'face_detection': False,
            'edge_detection': False,
            'blur': False,
            'grayscale': False,
            'motion_detection': False,
            'object_tracking': False,
            'advanced_analysis': False,  # New option for advanced processing
            'brightness': 0,
            'contrast': 1.0,
            'saturation': 1.0
        }
        
        # Motion detection variables
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2()
        self.motion_threshold = 500
        
        # Object tracking variables
        self.tracker = None
        self.tracking_box = None
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'faces_detected': 0,
            'motion_events': 0,
            'processing_time': 0,
            'start_time': time.time(),
            'advanced_analysis_count': 0,
            'quality_scores': []
        }
        
        # AWS S3 for cloud storage
        self.s3_client = None
        self.kinesis_client = None
        self.initialize_aws()
        
    def initialize_aws(self):
        """Initialize AWS clients"""
        try:
            # S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            
            # Kinesis client for real-time streaming
            self.kinesis_client = boto3.client(
                'kinesis',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            
            logger.info("AWS clients initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize AWS clients: {e}")
    
    def start_camera(self, camera_index=0):
        """Start camera capture"""
        try:
            self.cap = cv2.VideoCapture(camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            if not self.cap.isOpened():
                raise Exception("Cannot open camera")
                
            logger.info(f"Camera {camera_index} started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop camera capture"""
        if self.cap:
            self.cap.release()
            self.cap = None
            logger.info("Camera stopped")
    
    def process_frame(self, frame):
        """Apply various processing filters to the frame"""
        start_time = time.time()
        processed_frame = frame.copy()
        
        # Brightness and contrast adjustment
        if self.processing_options['brightness'] != 0 or self.processing_options['contrast'] != 1.0:
            processed_frame = cv2.convertScaleAbs(
                processed_frame, 
                alpha=self.processing_options['contrast'], 
                beta=self.processing_options['brightness']
            )
        
        # Grayscale conversion
        if self.processing_options['grayscale']:
            processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
            processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_GRAY2BGR)
        
        # Blur effect
        if self.processing_options['blur']:
            processed_frame = cv2.GaussianBlur(processed_frame, (15, 15), 0)
        
        # Edge detection
        if self.processing_options['edge_detection']:
            gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            processed_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # Face detection
        if self.processing_options['face_detection']:
            self.detect_faces(processed_frame)
        
        # Motion detection
        if self.processing_options['motion_detection']:
            self.detect_motion(processed_frame)
        
        # Object tracking
        if self.processing_options['object_tracking'] and self.tracker:
            self.track_object(processed_frame)
        
        # Advanced analysis
        if self.processing_options.get('advanced_analysis', False) and self.advanced_processor:
            try:
                # Get comprehensive analysis
                analysis_result = self.advanced_processor.comprehensive_analysis(processed_frame)
                
                # Draw annotations
                processed_frame = self.advanced_processor.draw_comprehensive_annotations(
                    processed_frame, analysis_result
                )
                
                # Update stats
                self.stats['advanced_analysis_count'] += 1
                if 'quality_scores' not in self.stats:
                    self.stats['quality_scores'] = []
                
                quality_score = analysis_result.get('quality_score', 0)
                self.stats['quality_scores'].append(quality_score)
                
                # Keep only last 100 quality scores
                if len(self.stats['quality_scores']) > 100:
                    self.stats['quality_scores'] = self.stats['quality_scores'][-100:]
                    
                # Send to Kinesis
                self.send_to_kinesis(analysis_result)
                
            except Exception as e:
                logger.error(f"Advanced analysis failed: {e}")
        
        # Update statistics
        processing_time = time.time() - start_time
        self.stats['frames_processed'] += 1
        self.stats['processing_time'] += processing_time
        
        return processed_frame
    
    def detect_faces(self, frame):
        """Detect and highlight faces in the frame"""
        if self.face_cascade is None:
            return  # Skip if cascade not loaded
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in faces:
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Detect eyes within face region if eye cascade is available
            if self.eye_cascade is not None:
                roi_gray = gray[y:y+h, x:x+w]
                roi_color = frame[y:y+h, x:x+w]
                eyes = self.eye_cascade.detectMultiScale(roi_gray)
                
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)
            
            # Add face label
            cv2.putText(frame, 'Face', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
        
        self.stats['faces_detected'] += len(faces)
    
    def detect_motion(self, frame):
        """Detect motion in the frame"""
        fg_mask = self.background_subtractor.apply(frame)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > self.motion_threshold:
                motion_detected = True
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
                cv2.putText(frame, 'Motion', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        if motion_detected:
            self.stats['motion_events'] += 1
    
    def track_object(self, frame):
        """Track selected object in the frame"""
        if self.tracker and self.tracking_box:
            success, box = self.tracker.update(frame)
            
            if success:
                (x, y, w, h) = [int(v) for v in box]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(frame, 'Tracking', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(frame, 'Tracking Lost', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    def start_tracking(self, frame, bbox):
        """Initialize object tracking with OpenCV version compatibility"""
        self.tracker = None
        
        # Try different tracker APIs based on OpenCV version
        tracker_created = False
        
        # Try OpenCV 4.5.1+ legacy API
        try:
            self.tracker = cv2.legacy.TrackerCSRT_create()
            tracker_created = True
            logger.info("Using legacy CSRT tracker")
        except (AttributeError, cv2.error):
            pass
        
        # Try OpenCV 4.5.4+ new API
        if not tracker_created:
            try:
                self.tracker = cv2.TrackerCSRT.create()
                tracker_created = True
                logger.info("Using new CSRT tracker")
            except (AttributeError, cv2.error):
                pass
        
        # Try legacy KCF tracker as fallback
        if not tracker_created:
            try:
                self.tracker = cv2.legacy.TrackerKCF_create()
                tracker_created = True
                logger.info("Using legacy KCF tracker")
            except (AttributeError, cv2.error):
                pass
        
        # Try new KCF tracker
        if not tracker_created:
            try:
                self.tracker = cv2.TrackerKCF.create()
                tracker_created = True
                logger.info("Using new KCF tracker")
            except (AttributeError, cv2.error):
                pass
        
        # Final fallback - disable tracking
        if not tracker_created:
            logger.warning("No compatible tracker found. Object tracking disabled.")
            self.tracker = None
            return False
        
        # Initialize tracker
        self.tracking_box = bbox
        try:
            success = self.tracker.init(frame, bbox)
            if success:
                logger.info(f"Object tracking started with bbox: {bbox}")
                return True
            else:
                logger.warning(f"Failed to initialize tracker with bbox: {bbox}")
                self.tracker = None
                return False
        except Exception as e:
            logger.error(f"Error initializing tracker: {e}")
            self.tracker = None
            return False
    
    def get_frame(self):
        """Get processed frame for streaming"""
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        if self.processing_enabled:
            frame = self.process_frame(frame)
        
        # Add overlay information
        self.add_overlay_info(frame)
        
        return frame
    
    def add_overlay_info(self, frame):
        """Add overlay information to the frame"""
        height, width = frame.shape[:2]
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add processing status
        status = "Processing: ON" if self.processing_enabled else "Processing: OFF"
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if self.processing_enabled else (0, 0, 255), 2)
        
        # Add frame counter
        cv2.putText(frame, f"Frames: {self.stats['frames_processed']}", (width - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def save_frame(self, frame, filename=None):
        """Save frame to local storage and optionally to cloud"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"frame_{timestamp}.jpg"
        
        # Save locally
        local_path = os.path.join('saved_frames', filename)
        os.makedirs('saved_frames', exist_ok=True)
        cv2.imwrite(local_path, frame)
        
        # Save to S3 if available
        if self.s3_client:
            try:
                bucket_name = os.getenv('S3_BUCKET_NAME', 'video-processing-frames')
                self.s3_client.upload_file(local_path, bucket_name, f"frames/{filename}")
                logger.info(f"Frame uploaded to S3: {filename}")
            except Exception as e:
                logger.error(f"Failed to upload frame to S3: {e}")
        
        return local_path
    
    def send_to_kinesis(self, analysis_result):
        """Send analysis results to Kinesis stream"""
        if not self.kinesis_client:
            return
            
        try:
            stream_name = os.getenv('KINESIS_STREAM_NAME', 'video-analytics-stream')
            data = {
                'timestamp': time.time(),
                'analysis': analysis_result,
                'source': 'web-app',
                'session_id': str(int(self.stats['start_time'])),
                'frame_id': self.stats['frames_processed']
            }
            
            response = self.kinesis_client.put_record(
                StreamName=stream_name,
                Data=json.dumps(data),
                PartitionKey=str(data['timestamp'])
            )
            
            logger.debug(f"Data sent to Kinesis: {response['SequenceNumber']}")
        except Exception as e:
            logger.error(f"Failed to send data to Kinesis: {e}")
    
    def get_stats(self):
        """Get processing statistics"""
        runtime = time.time() - self.stats['start_time']
        fps = self.stats['frames_processed'] / runtime if runtime > 0 else 0
        avg_processing_time = self.stats['processing_time'] / self.stats['frames_processed'] if self.stats['frames_processed'] > 0 else 0
        
        # Basic stats
        stats = {
            'frames_processed': self.stats['frames_processed'],
            'faces_detected': self.stats['faces_detected'],
            'motion_events': self.stats['motion_events'],
            'runtime_seconds': round(runtime, 2),
            'fps': round(fps, 2),
            'avg_processing_time_ms': round(avg_processing_time * 1000, 2),
            'processing_enabled': self.processing_enabled
        }
        
        # Add advanced analytics if available
        if self.advanced_processor:
            # Get quality scores
            quality_scores = self.stats.get('quality_scores', [])
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
                stats['avg_quality_score'] = round(avg_quality, 2)
                stats['max_quality_score'] = round(max(quality_scores), 2)
                stats['min_quality_score'] = round(min(quality_scores), 2)
            
            # Add count of advanced analyses
            stats['advanced_analysis_count'] = self.stats.get('advanced_analysis_count', 0)
            
            # Add advanced processor stats if available
            if hasattr(self.advanced_processor, 'get_analytics_summary'):
                advanced_stats = self.advanced_processor.get_analytics_summary()
                stats['advanced'] = advanced_stats
                
        return stats

# Global video processor instance
video_processor = VideoProcessor()

def generate_frames():
    """Generate video frames for streaming"""
    while True:
        frame = video_processor.get_frame()
        if frame is None:
            time.sleep(0.1)
            continue
        
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/start_camera', methods=['POST'])
def start_camera():
    """Start camera API endpoint"""
    data = request.get_json()
    camera_index = data.get('camera_index', 0)
    
    success = video_processor.start_camera(camera_index)
    return jsonify({'success': success, 'message': 'Camera started' if success else 'Failed to start camera'})

@app.route('/api/stop_camera', methods=['POST'])
def stop_camera():
    """Stop camera API endpoint"""
    video_processor.stop_camera()
    return jsonify({'success': True, 'message': 'Camera stopped'})

@app.route('/api/toggle_processing', methods=['POST'])
def toggle_processing():
    """Toggle video processing"""
    video_processor.processing_enabled = not video_processor.processing_enabled
    return jsonify({
        'success': True, 
        'processing_enabled': video_processor.processing_enabled,
        'message': f"Processing {'enabled' if video_processor.processing_enabled else 'disabled'}"
    })

@app.route('/api/update_options', methods=['POST'])
def update_options():
    """Update processing options"""
    data = request.get_json()
    video_processor.processing_options.update(data)
    return jsonify({'success': True, 'options': video_processor.processing_options})

@app.route('/api/get_options', methods=['GET'])
def get_options():
    """Get current processing options"""
    return jsonify(video_processor.processing_options)

@app.route('/api/save_frame', methods=['POST'])
def save_frame():
    """Save current frame"""
    frame = video_processor.get_frame()
    if frame is None:
        return jsonify({'success': False, 'message': 'No frame available'})
    
    try:
        path = video_processor.save_frame(frame)
        return jsonify({'success': True, 'path': path, 'message': 'Frame saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to save frame: {str(e)}'})

@app.route('/api/start_tracking', methods=['POST'])
def start_tracking():
    """Start object tracking"""
    data = request.get_json()
    bbox = data.get('bbox')  # [x, y, width, height]
    
    frame = video_processor.get_frame()
    if frame is None:
        return jsonify({'success': False, 'message': 'No frame available'})
    
    try:
        video_processor.start_tracking(frame, tuple(bbox))
        video_processor.processing_options['object_tracking'] = True
        return jsonify({'success': True, 'message': 'Object tracking started'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to start tracking: {str(e)}'})

@app.route('/api/stop_tracking', methods=['POST'])
def stop_tracking():
    """Stop object tracking"""
    video_processor.tracker = None
    video_processor.tracking_box = None
    video_processor.processing_options['object_tracking'] = False
    return jsonify({'success': True, 'message': 'Object tracking stopped'})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get processing statistics"""
    return jsonify(video_processor.get_stats())

@app.route('/api/reset_stats', methods=['POST'])
def reset_stats():
    """Reset processing statistics"""
    video_processor.stats = {
        'frames_processed': 0,
        'faces_detected': 0,
        'motion_events': 0,
        'processing_time': 0,
        'start_time': time.time()
    }
    return jsonify({'success': True, 'message': 'Statistics reset'})

@app.route('/api/advanced_options', methods=['GET'])
def get_advanced_options():
    """Get advanced processing options and availability"""
    options = {
        'advanced_processor_available': ADVANCED_PROCESSOR_AVAILABLE,
        'cloud_storage_available': video_processor.s3_client is not None,
        'streaming_available': video_processor.kinesis_client is not None,
        'current_settings': {
            'advanced_analysis': video_processor.processing_options.get('advanced_analysis', False)
        },
        'available_models': []
    }
    
    # Add available models if advanced processor is available
    if ADVANCED_PROCESSOR_AVAILABLE and video_processor.advanced_processor:
        options['available_models'] = [
            {'name': 'face_detection', 'available': True, 'type': 'opencv'},
            {'name': 'motion_detection', 'available': True, 'type': 'opencv'},
            {'name': 'edge_detection', 'available': True, 'type': 'opencv'},
            {'name': 'color_analysis', 'available': True, 'type': 'opencv'}
        ]
        
    return jsonify(options)

@app.route('/api/cloud_upload', methods=['POST'])
def cloud_upload():
    """Upload current processed frame to cloud storage"""
    if not video_processor.s3_client:
        return jsonify({
            'success': False,
            'message': 'Cloud storage not configured. Set AWS credentials in .env file.'
        })
        
    frame = video_processor.get_frame()
    if frame is None:
        return jsonify({'success': False, 'message': 'No frame available'})
    
    # If advanced processing is enabled, get analysis
    analysis = None
    if (video_processor.processing_options.get('advanced_analysis', False) and 
        video_processor.advanced_processor):
        try:
            analysis = video_processor.advanced_processor.comprehensive_analysis(frame)
        except Exception as e:
            logger.error(f"Error getting analysis: {e}")
    
    try:
        # Save frame as image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_path = f"saved_frames/frame_{timestamp}.jpg"
        os.makedirs('saved_frames', exist_ok=True)
        cv2.imwrite(local_path, frame)
        
        # Upload to S3
        bucket_name = os.getenv('S3_BUCKET_NAME', 'video-processing-frames')
        s3_key = f"frames/frame_{timestamp}.jpg"
        
        video_processor.s3_client.upload_file(
            local_path, 
            bucket_name, 
            s3_key
        )
        
        # Upload analysis if available
        if analysis:
            json_path = f"saved_frames/analysis_{timestamp}.json"
            with open(json_path, 'w') as f:
                json.dump(analysis, f)
                
            analysis_key = f"analysis/analysis_{timestamp}.json"
            video_processor.s3_client.upload_file(
                json_path,
                bucket_name,
                analysis_key
            )
        
        cloud_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        return jsonify({
            'success': True,
            'message': 'Frame uploaded to cloud storage',
            'local_path': local_path,
            'cloud_url': cloud_url,
            'analysis_available': analysis is not None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to upload to cloud: {str(e)}'
        })
    
@app.route('/api/model_download', methods=['POST'])
def download_models():
    """Download ML models from cloud storage"""
    try:
        # Import the cloud model sync function
        from cloud_model_sync import download_models_from_s3
        
        success = download_models_from_s3()
        if success:
            return jsonify({
                'success': True,
                'message': 'Models downloaded successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to download models'
            })
    except ImportError:
        return jsonify({
            'success': False,
            'message': 'Model sync functionality not available'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error downloading models: {str(e)}'
        })

@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    """Upload video file for processing"""
    if 'video' not in request.files:
        return jsonify({'success': False, 'message': 'No video file provided'})
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    try:
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"uploaded_video_{timestamp}.mp4"
        upload_path = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        
        file.save(upload_path)
        
        # If cloud storage is available, upload to S3
        if video_processor.s3_client:
            bucket_name = os.getenv('S3_BUCKET_NAME', 'video-processing-frames')
            s3_key = f"uploads/{filename}"
            
            video_processor.s3_client.upload_file(
                upload_path,
                bucket_name,
                s3_key
            )
            
            cloud_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        else:
            cloud_url = None
        
        return jsonify({
            'success': True,
            'message': 'Video uploaded successfully',
            'local_path': upload_path,
            'cloud_url': cloud_url,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to upload video: {str(e)}'
        })

@app.route('/api/stream_config', methods=['GET', 'POST'])
def stream_config():
    """Get or update streaming configuration"""
    if request.method == 'GET':
        config = {
            'kinesis_stream': os.getenv('KINESIS_STREAM_NAME', 'video-analytics-stream'),
            's3_bucket': os.getenv('S3_BUCKET_NAME', 'video-processing-frames'),
            'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
            'streaming_enabled': video_processor.kinesis_client is not None
        }
        return jsonify(config)
    
    elif request.method == 'POST':
        data = request.get_json()
        # Update environment variables (for current session only)
        if 'kinesis_stream' in data:
            os.environ['KINESIS_STREAM_NAME'] = data['kinesis_stream']
        if 's3_bucket' in data:
            os.environ['S3_BUCKET_NAME'] = data['s3_bucket']
        if 'aws_region' in data:
            os.environ['AWS_REGION'] = data['aws_region']
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated (session only)'
        })

@app.route('/api/export_data', methods=['POST'])
def export_data():
    """Export processing data and analytics"""
    try:
        data = request.get_json()
        export_format = data.get('format', 'json')  # json, csv
        
        # Get current stats
        stats = video_processor.get_stats()
        
        # Add session info
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'session_start': datetime.fromtimestamp(video_processor.stats['start_time']).isoformat(),
            'processing_options': video_processor.processing_options,
            'statistics': stats,
            'system_info': {
                'advanced_processor': ADVANCED_PROCESSOR_AVAILABLE,
                'cloud_enabled': video_processor.s3_client is not None,
                'streaming_enabled': video_processor.kinesis_client is not None
            }
        }
        
        # Create export file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = ""
        filepath = ""
        
        if export_format == 'json':
            filename = f"video_analytics_export_{timestamp}.json"
            filepath = os.path.join('exports', filename)
            os.makedirs('exports', exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
                
        elif export_format == 'csv':
            try:
                import pandas as pd
                filename = f"video_analytics_export_{timestamp}.csv"
                filepath = os.path.join('exports', filename)
                os.makedirs('exports', exist_ok=True)
                
                # Convert stats to DataFrame
                df = pd.DataFrame([stats])
                df.to_csv(filepath, index=False)
            except ImportError:
                return jsonify({
                    'success': False,
                    'message': 'pandas not installed - CSV export not available'
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Unsupported export format: {export_format}'
            })
        
        return jsonify({
            'success': True,
            'message': f'Data exported to {filename}',
            'filepath': filepath,
            'format': export_format
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Export failed: {str(e)}'
        })

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and container orchestration"""
    try:
        # Check critical services
        app_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'video-processor',
            'version': '1.0.0'
        }
        
        # Check if video processor is initialized
        app_status['video_processor'] = {
            'initialized': video_processor is not None,
            'advanced_processor': ADVANCED_PROCESSOR_AVAILABLE
        }
        
        # Check cloud connectivity if configured
        if os.getenv('AWS_ACCESS_KEY_ID'):
            try:
                # Simple S3 check
                if video_processor.s3_client:
                    _ = video_processor.s3_client.list_buckets()
                    app_status['aws_s3'] = 'connected'
                else:
                    app_status['aws_s3'] = 'not_initialized'
            except Exception as e:
                app_status['aws_s3'] = f'error: {str(e)}'
        
        return jsonify(app_status)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Check for required dependencies
    try:
        import cv2
        import numpy as np
        from PIL import Image
        logger.info("Core dependencies verified")
    except ImportError as e:
        logger.error(f"Missing required dependency: {e}")
        sys.exit(1)
    
    # Initialize models directory
    os.makedirs('models', exist_ok=True)
    os.makedirs('saved_frames', exist_ok=True)
    
    # Load environment variables and show status
    logger.info("=== Real-time Video Processing Platform ===")
    logger.info(f"Advanced Processor: {'Available' if ADVANCED_PROCESSOR_AVAILABLE else 'Not Available'}")
    logger.info(f"AWS S3: {'Configured' if video_processor.s3_client else 'Not Configured'}")
    logger.info(f"AWS Kinesis: {'Configured' if video_processor.kinesis_client else 'Not Configured'}")
    
    # Show configuration hints if cloud services not configured
    if not video_processor.s3_client:
        logger.info("💡 To enable cloud features, set AWS credentials in .env file")
    
    if not ADVANCED_PROCESSOR_AVAILABLE:
        logger.info("💡 To enable advanced analysis, ensure all ML dependencies are installed")
    
    # Start the Flask application
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Web interface: http://localhost:{port}")
    
    app.run(debug=debug, host=host, port=port, threaded=True)
