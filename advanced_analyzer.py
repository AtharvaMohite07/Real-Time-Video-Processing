import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
import time
import os

logger = logging.getLogger(__name__)

class AdvancedVideoProcessor:
    """Enhanced video processor with advanced computer vision capabilities"""
    
    def __init__(self):
        self.initialize_models()
        self.metrics = {
            'total_frames': 0,
            'objects_detected': 0,
            'faces_detected': 0,
            'processing_times': []
        }
    
    def initialize_models(self):
        """Initialize available models"""
        try:
            # OpenCV cascade classifiers - use full paths as fallback
            try:
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
                self.smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
            except:
                # Fallback to default constructors
                self.face_cascade = cv2.CascadeClassifier()
                self.eye_cascade = cv2.CascadeClassifier()
                self.smile_cascade = cv2.CascadeClassifier()
            
            # Background subtractor for motion detection
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2()
            
            # Corner detection
            self.corner_detector = cv2.goodFeaturesToTrack
            
            # Edge detection parameters
            self.canny_params = {'threshold1': 50, 'threshold2': 150}
            
            logger.info("Advanced video processor initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
    
    def detect_faces_advanced(self, frame: np.ndarray) -> List[Dict]:
        """Advanced face detection with additional features"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        face_data = []
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            color_roi = frame[y:y+h, x:x+w]
            
            # Detect eyes within face
            eyes = self.eye_cascade.detectMultiScale(face_roi)
            
            # Detect smile
            smiles = self.smile_cascade.detectMultiScale(face_roi, 1.8, 20)
            
            face_info = {
                'bbox': [x, y, w, h],
                'eyes_count': len(eyes),
                'smile_detected': len(smiles) > 0,
                'area': w * h,
                'aspect_ratio': w / h
            }
            
            face_data.append(face_info)
        
        return face_data
    
    def detect_motion_advanced(self, frame: np.ndarray) -> Dict:
        """Advanced motion detection with tracking"""
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Noise reduction
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_objects = []
        total_motion_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # Filter small noise
                x, y, w, h = cv2.boundingRect(contour)
                motion_objects.append({
                    'bbox': [x, y, w, h],
                    'area': area,
                    'centroid': [x + w//2, y + h//2]
                })
                total_motion_area += area
        
        return {
            'objects': motion_objects,
            'total_area': total_motion_area,
            'motion_intensity': total_motion_area / (frame.shape[0] * frame.shape[1])
        }
    
    def detect_edges_advanced(self, frame: np.ndarray) -> np.ndarray:
        """Advanced edge detection with multiple methods"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Canny edge detection
        edges = cv2.Canny(blurred, self.canny_params['threshold1'], self.canny_params['threshold2'])
        
        # Dilate edges to make them more visible
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        return edges
    
    def detect_corners(self, frame: np.ndarray) -> List[Tuple[int, int]]:
        """Detect corner features in the frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        corners = cv2.goodFeaturesToTrack(
            gray,
            maxCorners=100,
            qualityLevel=0.01,
            minDistance=10,
            blockSize=3
        )
        
        corner_points = []
        if corners is not None:
            corners = corners.reshape(-1, 2).astype(int)
            for corner in corners:
                x, y = corner
                corner_points.append((int(x), int(y)))
        
        return corner_points
    
    def analyze_color_histogram(self, frame: np.ndarray) -> Dict:
        """Analyze color distribution in the frame"""
        # Calculate histograms for each channel
        hist_b = cv2.calcHist([frame], [0], None, [256], [0, 256])
        hist_g = cv2.calcHist([frame], [1], None, [256], [0, 256])
        hist_r = cv2.calcHist([frame], [2], None, [256], [0, 256])
        
        # Calculate dominant colors
        dominant_b = np.argmax(hist_b)
        dominant_g = np.argmax(hist_g)
        dominant_r = np.argmax(hist_r)
        
        # Calculate mean colors
        mean_b = np.mean(frame[:, :, 0])
        mean_g = np.mean(frame[:, :, 1])
        mean_r = np.mean(frame[:, :, 2])
        
        return {
            'dominant_color': [int(dominant_r), int(dominant_g), int(dominant_b)],
            'mean_color': [int(mean_r), int(mean_g), int(mean_b)],
            'brightness': float(np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)))
        }
    
    def comprehensive_analysis(self, frame: np.ndarray) -> Dict:
        """Perform comprehensive video analysis"""
        start_time = time.time()
        
        # Basic frame info
        height, width = frame.shape[:2]
        
        # Face detection
        faces = self.detect_faces_advanced(frame)
        
        # Motion detection
        motion_data = self.detect_motion_advanced(frame)
        
        # Corner detection
        corners = self.detect_corners(frame)
        
        # Color analysis
        color_analysis = self.analyze_color_histogram(frame)
        
        # Edge detection
        edges = self.detect_edges_advanced(frame)
        edge_density = np.sum(edges > 0) / (height * width)
        
        processing_time = time.time() - start_time
        
        analysis_result = {
            'timestamp': time.time(),
            'frame_size': [width, height],
            'faces': faces,
            'motion': motion_data,
            'corners_count': len(corners),
            'corners': corners[:20],  # Limit to first 20 corners
            'color_analysis': color_analysis,
            'edge_density': edge_density,
            'processing_time': processing_time,
            'quality_score': self.calculate_quality_score(faces, motion_data, edge_density)
        }
        
        # Update metrics
        self.update_metrics(analysis_result)
        
        return analysis_result
    
    def calculate_quality_score(self, faces: List[Dict], motion_data: Dict, edge_density: float) -> float:
        """Calculate a quality score for the frame"""
        score = 0.0
        
        # Face quality (0-40 points)
        if faces:
            face_score = min(len(faces) * 10, 40)
            # Bonus for well-sized faces
            for face in faces:
                if 50 < face['area'] < 10000:  # Good face size
                    face_score += 5
            score += min(face_score, 40)
        
        # Motion quality (0-30 points)
        motion_intensity = motion_data.get('motion_intensity', 0)
        if 0.01 < motion_intensity < 0.3:  # Good amount of motion
            score += 30
        elif motion_intensity > 0:
            score += 15
        
        # Edge quality (0-30 points)
        if 0.1 < edge_density < 0.4:  # Good amount of detail
            score += 30
        elif edge_density > 0:
            score += 15
        
        return min(score, 100.0)
    
    def draw_comprehensive_annotations(self, frame: np.ndarray, analysis_result: Dict) -> np.ndarray:
        """Draw comprehensive annotations on the frame"""
        annotated_frame = frame.copy()
        
        # Draw faces
        for face in analysis_result.get('faces', []):
            x, y, w, h = face['bbox']
            color = (0, 255, 0) if face['smile_detected'] else (255, 0, 0)
            cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), color, 2)
            
            # Face info
            info = f"Eyes: {face['eyes_count']}"
            if face['smile_detected']:
                info += " | Smile"
            cv2.putText(annotated_frame, info, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Draw motion objects
        for motion_obj in analysis_result.get('motion', {}).get('objects', []):
            x, y, w, h = motion_obj['bbox']
            cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            cv2.putText(annotated_frame, 'Motion', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Draw corners
        for corner in analysis_result.get('corners', []):
            cv2.circle(annotated_frame, corner, 3, (255, 255, 0), -1)
        
        # Draw quality score
        quality_score = analysis_result.get('quality_score', 0)
        score_color = (0, 255, 0) if quality_score > 70 else (0, 255, 255) if quality_score > 40 else (0, 0, 255)
        cv2.putText(annotated_frame, f"Quality: {quality_score:.1f}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, score_color, 2)
        
        # Draw processing time
        proc_time = analysis_result.get('processing_time', 0) * 1000
        cv2.putText(annotated_frame, f"Processing: {proc_time:.1f}ms", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return annotated_frame
    
    def update_metrics(self, analysis_result: Dict):
        """Update processing metrics"""
        self.metrics['total_frames'] += 1
        self.metrics['faces_detected'] += len(analysis_result.get('faces', []))
        self.metrics['objects_detected'] += len(analysis_result.get('motion', {}).get('objects', []))
        self.metrics['processing_times'].append(analysis_result.get('processing_time', 0))
        
        # Keep only last 100 processing times
        if len(self.metrics['processing_times']) > 100:
            self.metrics['processing_times'] = self.metrics['processing_times'][-100:]
    
    def get_analytics_summary(self) -> Dict:
        """Get comprehensive analytics summary"""
        avg_processing_time = np.mean(self.metrics['processing_times']) if self.metrics['processing_times'] else 0
        
        return {
            'total_frames_processed': self.metrics['total_frames'],
            'total_faces_detected': self.metrics['faces_detected'],
            'total_objects_detected': self.metrics['objects_detected'],
            'average_processing_time_ms': avg_processing_time * 1000,
            'estimated_fps': 1 / avg_processing_time if avg_processing_time > 0 else 0,
            'faces_per_frame': self.metrics['faces_detected'] / max(self.metrics['total_frames'], 1),
            'objects_per_frame': self.metrics['objects_detected'] / max(self.metrics['total_frames'], 1)
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            'total_frames': 0,
            'objects_detected': 0,
            'faces_detected': 0,
            'processing_times': []
        }
