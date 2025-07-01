import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
import time


# Optional imports with fallbacks
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

logger = logging.getLogger(__name__)

class AdvancedVideoAnalyzer:
    """Advanced video analyzer with multiple AI models"""
    
    def __init__(self, model_paths: Optional[Dict[str, str]] = None):
        self.model_paths = model_paths or {}
        self.models = {}
        self.initialize_models()
        
    def initialize_models(self):
        """Initialize all AI models"""
        try:
            # YOLO for object detection
            self.load_yolo_model()
            
            # MediaPipe for pose estimation
            self.load_mediapipe_models()
            
            # Face recognition model
            self.load_face_recognition_model()
            
            logger.info("All AI models loaded successfully")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def load_yolo_model(self):
        """Load YOLO model for object detection"""
        if not YOLO_AVAILABLE:
            logger.warning("YOLO not available - install ultralytics package")
            self.models['yolo'] = None
            return
            
        try:
            model_path = self.model_paths.get('yolo', 'yolov8n.pt')
            self.models['yolo'] = YOLO(model_path)
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.warning(f"YOLO model not available: {e}")
            self.models['yolo'] = None
    
    def load_mediapipe_models(self):
        """Load MediaPipe models"""
        if not MEDIAPIPE_AVAILABLE:
            logger.warning("MediaPipe not available - install mediapipe package")
            return
            
        try:
            # Pose estimation
            self.models['pose'] = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                enable_segmentation=True,
                min_detection_confidence=0.5
            )
            
            # Hand tracking
            self.models['hands'] = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5
            )
            
            # Face mesh
            self.models['face_mesh'] = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5
            )
            
            logger.info("MediaPipe models loaded successfully")
        except Exception as e:
            logger.warning(f"MediaPipe models not available: {e}")
    
    def load_face_recognition_model(self):
        """Load face recognition model"""
        try:
            # This would load a pre-trained face recognition model
            # For now, we'll use OpenCV's cascade classifier
            self.models['face_cascade'] = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            logger.info("Face recognition model loaded successfully")
        except Exception as e:
            logger.warning(f"Face recognition model not available: {e}")
    
    def detect_objects(self, frame: np.ndarray) -> List[Dict]:
        """Detect objects using YOLO"""
        if not self.models.get('yolo'):
            return []
        
        try:
            results = self.models['yolo'](frame)
            objects = []
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = self.models['yolo'].names[class_id]
                        
                        objects.append({
                            'class': class_name,
                            'confidence': float(confidence),
                            'bbox': [int(x1), int(y1), int(x2), int(y2)]
                        })
            
            return objects
        except Exception as e:
            logger.error(f"Error in object detection: {e}")
            return []
    
    def detect_pose(self, frame: np.ndarray) -> Dict:
        """Detect human pose using MediaPipe"""
        if not self.models.get('pose'):
            return {}
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.models['pose'].process(rgb_frame)
            
            if results.pose_landmarks:
                landmarks = []
                for landmark in results.pose_landmarks.landmark:
                    landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z,
                        'visibility': landmark.visibility
                    })
                
                return {
                    'landmarks': landmarks,
                    'segmentation_mask': results.segmentation_mask is not None
                }
            
            return {}
        except Exception as e:
            logger.error(f"Error in pose detection: {e}")
            return {}
    
    def detect_hands(self, frame: np.ndarray) -> List[Dict]:
        """Detect hands using MediaPipe"""
        if not self.models.get('hands'):
            return []
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.models['hands'].process(rgb_frame)
            
            hands = []
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    landmarks = []
                    for landmark in hand_landmarks.landmark:
                        landmarks.append({
                            'x': landmark.x,
                            'y': landmark.y,
                            'z': landmark.z
                        })
                    hands.append({'landmarks': landmarks})
            
            return hands
        except Exception as e:
            logger.error(f"Error in hand detection: {e}")
            return []
    
    def analyze_face_mesh(self, frame: np.ndarray) -> Dict:
        """Analyze face mesh using MediaPipe"""
        if not self.models.get('face_mesh'):
            return {}
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.models['face_mesh'].process(rgb_frame)
            
            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
                landmarks = []
                for landmark in face_landmarks.landmark:
                    landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z
                    })
                
                return {'landmarks': landmarks}
            
            return {}
        except Exception as e:
            logger.error(f"Error in face mesh analysis: {e}")
            return {}
    
    def comprehensive_analysis(self, frame: np.ndarray) -> Dict:
        """Perform comprehensive video analysis"""
        start_time = time.time()
        
        analysis_result = {
            'timestamp': time.time(),
            'frame_size': frame.shape,
            'objects': self.detect_objects(frame),
            'pose': self.detect_pose(frame),
            'hands': self.detect_hands(frame),
            'face_mesh': self.analyze_face_mesh(frame),
            'processing_time': 0
        }
        
        analysis_result['processing_time'] = time.time() - start_time
        
        return analysis_result
    
    def draw_annotations(self, frame: np.ndarray, analysis_result: Dict) -> np.ndarray:
        """Draw analysis annotations on frame"""
        annotated_frame = frame.copy()
        
        # Draw object detections
        for obj in analysis_result.get('objects', []):
            bbox = obj['bbox']
            label = f"{obj['class']}: {obj['confidence']:.2f}"
            
            cv2.rectangle(annotated_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            cv2.putText(annotated_frame, label, (bbox[0], bbox[1] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw pose landmarks
        pose_data = analysis_result.get('pose', {})
        if pose_data.get('landmarks'):
            mp_pose = mp.solutions.pose
            mp_draw = mp.solutions.drawing_utils
            
            # Convert normalized coordinates to pixel coordinates
            h, w = frame.shape[:2]
            landmarks = pose_data['landmarks']
            
            # Draw pose connections
            connections = mp_pose.POSE_CONNECTIONS
            for connection in connections:
                start_idx, end_idx = connection
                if start_idx < len(landmarks) and end_idx < len(landmarks):
                    start_point = landmarks[start_idx]
                    end_point = landmarks[end_idx]
                    
                    start_x = int(start_point['x'] * w)
                    start_y = int(start_point['y'] * h)
                    end_x = int(end_point['x'] * w)
                    end_y = int(end_point['y'] * h)
                    
                    cv2.line(annotated_frame, (start_x, start_y), (end_x, end_y), (255, 0, 0), 2)
        
        # Draw hand landmarks
        hands_data = analysis_result.get('hands', [])
        for hand in hands_data:
            landmarks = hand.get('landmarks', [])
            h, w = frame.shape[:2]
            
            for landmark in landmarks:
                x = int(landmark['x'] * w)
                y = int(landmark['y'] * h)
                cv2.circle(annotated_frame, (x, y), 3, (255, 255, 0), -1)
        
        return annotated_frame


class RealTimeAnalytics:
    """Real-time analytics processor"""
    
    def __init__(self):
        self.analyzer = AdvancedVideoAnalyzer()
        self.metrics = {
            'total_frames': 0,
            'objects_detected': 0,
            'faces_detected': 0,
            'poses_detected': 0,
            'processing_times': []
        }
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Process a single frame and return annotated frame with analytics"""
        start_time = time.time()
        
        # Perform comprehensive analysis
        analysis_result = self.analyzer.comprehensive_analysis(frame)
        
        # Draw annotations
        annotated_frame = self.analyzer.draw_annotations(frame, analysis_result)
        
        # Update metrics
        self.update_metrics(analysis_result)
        
        processing_time = time.time() - start_time
        analysis_result['total_processing_time'] = processing_time
        
        return annotated_frame, analysis_result
    
    def update_metrics(self, analysis_result: Dict):
        """Update analytics metrics"""
        self.metrics['total_frames'] += 1
        self.metrics['objects_detected'] += len(analysis_result.get('objects', []))
        self.metrics['faces_detected'] += 1 if analysis_result.get('face_mesh', {}).get('landmarks') else 0
        self.metrics['poses_detected'] += 1 if analysis_result.get('pose', {}).get('landmarks') else 0
        self.metrics['processing_times'].append(analysis_result.get('processing_time', 0))
        
        # Keep only last 100 processing times for average calculation
        if len(self.metrics['processing_times']) > 100:
            self.metrics['processing_times'] = self.metrics['processing_times'][-100:]
    
    def get_analytics_summary(self) -> Dict:
        """Get analytics summary"""
        avg_processing_time = np.mean(self.metrics['processing_times']) if self.metrics['processing_times'] else 0
        
        return {
            'total_frames_processed': self.metrics['total_frames'],
            'total_objects_detected': self.metrics['objects_detected'],
            'total_faces_detected': self.metrics['faces_detected'],
            'total_poses_detected': self.metrics['poses_detected'],
            'average_processing_time_ms': avg_processing_time * 1000,
            'fps': 1 / avg_processing_time if avg_processing_time > 0 else 0,
            'objects_per_frame': self.metrics['objects_detected'] / max(self.metrics['total_frames'], 1),
            'detection_rate': {
                'faces': self.metrics['faces_detected'] / max(self.metrics['total_frames'], 1),
                'poses': self.metrics['poses_detected'] / max(self.metrics['total_frames'], 1)
            }
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            'total_frames': 0,
            'objects_detected': 0,
            'faces_detected': 0,
            'poses_detected': 0,
            'processing_times': []
        }
