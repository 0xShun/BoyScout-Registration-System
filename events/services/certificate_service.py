"""
Certificate generation service for event attendance certificates.
Handles certificate image generation using PIL/Pillow.
"""
import os
from io import BytesIO
from datetime import datetime
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont


class CertificateService:
    """Service for generating event attendance certificates"""
    
    DEFAULT_FONT_PATHS = [
        '/System/Library/Fonts/Supplemental/Arial.ttf',  # macOS
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
        'C:\\Windows\\Fonts\\arial.ttf',  # Windows
        '/Library/Fonts/Arial.ttf',  # macOS alternative
    ]
    
    # Certificate dimensions (A4 landscape in pixels at 150 DPI)
    CERT_WIDTH = 1754
    CERT_HEIGHT = 1240
    
    @staticmethod
    def generate_certificate(user, event, attendance):
        """
        Generate a certificate for a user's event attendance.
        Creates a simple, professional certificate without requiring a template.
        
        Args:
            user: User object
            event: Event object
            attendance: Attendance object
            
        Returns:
            EventCertificate object
        """
        from events.models import EventCertificate
        
        # Generate unique certificate number
        cert_number = EventCertificate.generate_certificate_number(event.id, user.id)
        
        # Create certificate image
        cert_image = CertificateService._create_basic_certificate(
            participant_name=user.get_full_name(),
            event_name=event.title,
            event_date=event.date,
            cert_number=cert_number
        )
        
        # Save certificate to file
        image_io = BytesIO()
        cert_image.save(image_io, format='PNG', quality=95)
        image_file = ContentFile(image_io.getvalue(), name=f'certificate_{cert_number}.png')
        
        # Create EventCertificate record
        certificate = EventCertificate.objects.create(
            user=user,
            event=event,
            attendance=attendance,
            certificate_number=cert_number,
            certificate_file=image_file
        )
        
        return certificate
    
    @staticmethod
    def _create_basic_certificate(participant_name, event_name, event_date, cert_number):
        """
        Create a simple, professional certificate without requiring a template.
        
        Args:
            participant_name: Full name of participant
            event_name: Name of the event
            event_date: Date object
            cert_number: Unique certificate number
            
        Returns:
            PIL Image object
        """
        # Create blank certificate with white background
        img = Image.new('RGB', (CertificateService.CERT_WIDTH, CertificateService.CERT_HEIGHT), '#FFFFFF')
        draw = ImageDraw.Draw(img)
        
        # Draw border
        border_margin = 50
        border_color = '#1E3A8A'  # Dark blue
        for i in range(10):
            draw.rectangle(
                [border_margin + i, border_margin + i, 
                 CertificateService.CERT_WIDTH - border_margin - i, 
                 CertificateService.CERT_HEIGHT - border_margin - i],
                outline=border_color
            )
        
        # Draw decorative corners
        corner_size = 100
        corner_color = '#3B82F6'  # Blue
        positions = [
            (border_margin + 20, border_margin + 20),  # Top-left
            (CertificateService.CERT_WIDTH - border_margin - corner_size - 20, border_margin + 20),  # Top-right
            (border_margin + 20, CertificateService.CERT_HEIGHT - border_margin - corner_size - 20),  # Bottom-left
            (CertificateService.CERT_WIDTH - border_margin - corner_size - 20, 
             CertificateService.CERT_HEIGHT - border_margin - corner_size - 20)  # Bottom-right
        ]
        
        for x, y in positions:
            draw.rectangle([x, y, x + corner_size, y + corner_size], fill=corner_color)
        
        # Get font path
        font_path = CertificateService._get_font_path()
        
        try:
            # Title: "CERTIFICATE OF ATTENDANCE"
            title_font = ImageFont.truetype(font_path, 70)
            title_text = "CERTIFICATE OF ATTENDANCE"
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (CertificateService.CERT_WIDTH - title_width) // 2
            title_y = 200
            draw.text((title_x, title_y), title_text, font=title_font, fill='#1E3A8A')
            
            # Subtitle: "This certificate is proudly presented to"
            subtitle_font = ImageFont.truetype(font_path, 30)
            subtitle_text = "This certificate is proudly presented to"
            subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (CertificateService.CERT_WIDTH - subtitle_width) // 2
            subtitle_y = 330
            draw.text((subtitle_x, subtitle_y), subtitle_text, font=subtitle_font, fill='#374151')
            
            # Participant name (larger, bold effect)
            name_font = ImageFont.truetype(font_path, 65)
            name_bbox = draw.textbbox((0, 0), participant_name, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_x = (CertificateService.CERT_WIDTH - name_width) // 2
            name_y = 420
            # Bold effect with multiple draws
            for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
                draw.text((name_x + offset[0], name_y + offset[1]), participant_name, 
                         font=name_font, fill='#1E40AF')
            
            # Decorative line under name
            line_y = name_y + 90
            line_margin = 400
            draw.line([line_margin, line_y, CertificateService.CERT_WIDTH - line_margin, line_y],
                     fill='#3B82F6', width=3)
            
            # Event details
            event_font = ImageFont.truetype(font_path, 35)
            event_text = "For participation in"
            event_bbox = draw.textbbox((0, 0), event_text, font=event_font)
            event_width = event_bbox[2] - event_bbox[0]
            event_x = (CertificateService.CERT_WIDTH - event_width) // 2
            event_y = 600
            draw.text((event_x, event_y), event_text, font=event_font, fill='#374151')
            
            # Event name (bold)
            event_name_font = ImageFont.truetype(font_path, 50)
            event_name_bbox = draw.textbbox((0, 0), event_name, font=event_name_font)
            event_name_width = event_name_bbox[2] - event_name_bbox[0]
            event_name_x = (CertificateService.CERT_WIDTH - event_name_width) // 2
            event_name_y = 670
            # Bold effect
            for offset in [(0, 0), (1, 0), (0, 1), (1, 1)]:
                draw.text((event_name_x + offset[0], event_name_y + offset[1]), event_name,
                         font=event_name_font, fill='#1E3A8A')
            
            # Date
            date_font = ImageFont.truetype(font_path, 32)
            date_str = event_date.strftime("%B %d, %Y")
            date_bbox = draw.textbbox((0, 0), date_str, font=date_font)
            date_width = date_bbox[2] - date_bbox[0]
            date_x = (CertificateService.CERT_WIDTH - date_width) // 2
            date_y = 780
            draw.text((date_x, date_y), date_str, font=date_font, fill='#6B7280')
            
            # Organization/Scout name
            org_font = ImageFont.truetype(font_path, 28)
            org_text = "Boy Scouts of the Philippines"
            org_bbox = draw.textbbox((0, 0), org_text, font=org_font)
            org_width = org_bbox[2] - org_bbox[0]
            org_x = (CertificateService.CERT_WIDTH - org_width) // 2
            org_y = 920
            draw.text((org_x, org_y), org_text, font=org_font, fill='#1E3A8A')
            
            # Certificate number (bottom right)
            cert_num_font = ImageFont.truetype(font_path, 20)
            cert_num_text = f"Certificate No: {cert_number}"
            draw.text((CertificateService.CERT_WIDTH - 400, CertificateService.CERT_HEIGHT - 100),
                     cert_num_text, font=cert_num_font, fill='#9CA3AF')
            
            # Issue date (bottom left)
            issue_date_text = f"Issued: {datetime.now().strftime('%B %d, %Y')}"
            draw.text((100, CertificateService.CERT_HEIGHT - 100),
                     issue_date_text, font=cert_num_font, fill='#9CA3AF')
            
        except Exception as e:
            # Fallback to default font if custom font fails
            print(f"Error loading font: {e}. Using default font.")
            default_font = ImageFont.load_default()
            draw.text((CertificateService.CERT_WIDTH // 2 - 200, 300), 
                     "CERTIFICATE OF ATTENDANCE", font=default_font, fill='#000000')
            draw.text((CertificateService.CERT_WIDTH // 2 - 150, 400), 
                     participant_name, font=default_font, fill='#000000')
            draw.text((CertificateService.CERT_WIDTH // 2 - 100, 500), 
                     event_name, font=default_font, fill='#000000')
            draw.text((CertificateService.CERT_WIDTH // 2 - 100, 600), 
                     event_date.strftime("%B %d, %Y"), font=default_font, fill='#000000')
        
        return img
    
    @staticmethod
    def _get_font_path():
        """
        Get path to a suitable TrueType font.
        
        Returns:
            Path to font file
        """
        # Try to find an available font
        for font_path in CertificateService.DEFAULT_FONT_PATHS:
            if os.path.exists(font_path):
                return font_path
        
        # If no font found, try to find any .ttf file in common locations
        search_paths = [
            '/System/Library/Fonts',
            '/Library/Fonts',
            '/usr/share/fonts',
            'C:\\Windows\\Fonts'
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        if file.endswith('.ttf'):
                            return os.path.join(root, file)
        
        # Fallback: return first path and let PIL handle the error
        return CertificateService.DEFAULT_FONT_PATHS[0]
