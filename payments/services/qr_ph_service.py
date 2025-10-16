"""
QR PH Service
Handles generation of QR PH compliant QR codes (EMVCo standard)
"""

import qrcode
import io
from decimal import Decimal
from typing import Optional, Tuple
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)


class QRPHService:
    """Service for generating QR PH compliant QR codes"""
    
    # EMVCo QR Code IDs
    PAYLOAD_FORMAT_INDICATOR = "00"
    POINT_OF_INITIATION = "01"
    MERCHANT_ACCOUNT_INFO = "26"
    MERCHANT_CATEGORY_CODE = "52"
    TRANSACTION_CURRENCY = "53"
    TRANSACTION_AMOUNT = "54"
    COUNTRY_CODE = "58"
    MERCHANT_NAME = "59"
    MERCHANT_CITY = "60"
    ADDITIONAL_DATA = "62"
    CRC = "63"
    
    @staticmethod
    def _calculate_crc16_ccitt(data: str) -> str:
        """
        Calculate CRC16-CCITT checksum for EMVCo QR code
        
        Args:
            data: QR code data string
            
        Returns:
            4-character hex string of CRC
        """
        crc = 0xFFFF
        polynomial = 0x1021
        
        for byte in data.encode('utf-8'):
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc <<= 1
                crc &= 0xFFFF
        
        return f"{crc:04X}"
    
    @staticmethod
    def _format_tlv(tag: str, value: str) -> str:
        """
        Format Tag-Length-Value for EMVCo QR
        
        Args:
            tag: 2-digit tag ID
            value: Value string
            
        Returns:
            Formatted TLV string
        """
        length = len(value)
        return f"{tag}{length:02d}{value}"
    
    @classmethod
    def generate_emvco_qr_string(
        cls,
        merchant_id: str,
        merchant_name: str,
        account_number: str,
        amount: Optional[Decimal] = None,
        reference: Optional[str] = None,
        merchant_city: str = "Manila"
    ) -> str:
        """
        Generate EMVCo-compliant QR code string for QR PH
        
        Args:
            merchant_id: Merchant identification code
            merchant_name: Business/merchant name
            account_number: Bank account or mobile number
            amount: Transaction amount (None for static QR)
            reference: Transaction reference number
            merchant_city: Merchant city
            
        Returns:
            EMVCo compliant QR string
        """
        try:
            qr_data = []
            
            # Payload Format Indicator (fixed: "01")
            qr_data.append(cls._format_tlv(cls.PAYLOAD_FORMAT_INDICATOR, "01"))
            
            # Point of Initiation Method
            # 11 = Static QR (reusable), 12 = Dynamic QR (one-time)
            if amount:
                qr_data.append(cls._format_tlv(cls.POINT_OF_INITIATION, "12"))
            else:
                qr_data.append(cls._format_tlv(cls.POINT_OF_INITIATION, "11"))
            
            # Merchant Account Information (ID 26-51)
            # This section varies by payment provider
            # Format: Sub-TLV within main TLV
            merchant_info_parts = []
            merchant_info_parts.append(cls._format_tlv("00", merchant_id))
            merchant_info_parts.append(cls._format_tlv("01", account_number))
            merchant_info = "".join(merchant_info_parts)
            qr_data.append(cls._format_tlv(cls.MERCHANT_ACCOUNT_INFO, merchant_info))
            
            # Merchant Category Code (MCC)
            # 0000 = Not classified
            qr_data.append(cls._format_tlv(cls.MERCHANT_CATEGORY_CODE, "0000"))
            
            # Transaction Currency (608 = PHP)
            qr_data.append(cls._format_tlv(cls.TRANSACTION_CURRENCY, "608"))
            
            # Transaction Amount (only for dynamic QR)
            if amount:
                amount_str = f"{amount:.2f}"
                qr_data.append(cls._format_tlv(cls.TRANSACTION_AMOUNT, amount_str))
            
            # Country Code (PH = Philippines)
            qr_data.append(cls._format_tlv(cls.COUNTRY_CODE, "PH"))
            
            # Merchant Name (max 25 characters)
            merchant_name_trimmed = merchant_name[:25]
            qr_data.append(cls._format_tlv(cls.MERCHANT_NAME, merchant_name_trimmed))
            
            # Merchant City (max 15 characters)
            merchant_city_trimmed = merchant_city[:15]
            qr_data.append(cls._format_tlv(cls.MERCHANT_CITY, merchant_city_trimmed))
            
            # Additional Data (reference number, etc.)
            if reference:
                additional_parts = []
                # Sub-ID 05 = Reference Label
                additional_parts.append(cls._format_tlv("05", reference[:25]))
                additional_data = "".join(additional_parts)
                qr_data.append(cls._format_tlv(cls.ADDITIONAL_DATA, additional_data))
            
            # Join all data
            qr_string = "".join(qr_data)
            
            # Add CRC placeholder
            qr_string += cls.CRC + "04"
            
            # Calculate and append actual CRC
            crc_value = cls._calculate_crc16_ccitt(qr_string)
            qr_string += crc_value
            
            logger.info(f"Generated QR PH string with length {len(qr_string)}")
            return qr_string
            
        except Exception as e:
            logger.error(f"Error generating EMVCo QR string: {str(e)}")
            raise
    
    @staticmethod
    def generate_qr_code_image(qr_string: str, box_size: int = 10, 
                               border: int = 4) -> ContentFile:
        """
        Generate QR code image from QR PH string
        
        Args:
            qr_string: EMVCo QR string
            box_size: Size of each box in pixels
            border: Border size in boxes
            
        Returns:
            ContentFile with PNG image data
        """
        try:
            qr = qrcode.QRCode(
                version=None,  # Auto-determine version
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=box_size,
                border=border,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to BytesIO
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            logger.info("Generated QR code image successfully")
            return ContentFile(buffer.read(), name='qr_ph_code.png')
            
        except Exception as e:
            logger.error(f"Error generating QR code image: {str(e)}")
            raise
    
    @classmethod
    def create_payment_qr_code(
        cls,
        merchant_id: str,
        merchant_name: str,
        account_number: str,
        amount: Optional[Decimal] = None,
        reference: Optional[str] = None,
        merchant_city: str = "Manila"
    ) -> Tuple[str, ContentFile]:
        """
        Create a complete QR PH payment QR code (string + image)
        
        Args:
            merchant_id: Merchant identification code
            merchant_name: Business/merchant name
            account_number: Bank account or mobile number
            amount: Transaction amount (None for static QR)
            reference: Transaction reference number
            merchant_city: Merchant city
            
        Returns:
            Tuple of (qr_string, qr_image_file)
        """
        # Generate QR string
        qr_string = cls.generate_emvco_qr_string(
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            account_number=account_number,
            amount=amount,
            reference=reference,
            merchant_city=merchant_city
        )
        
        # Generate QR code image
        qr_image = cls.generate_qr_code_image(qr_string)
        
        return qr_string, qr_image
