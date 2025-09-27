from io import BytesIO
from django.template.loader import get_template
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

def render_to_pdf(template_src, context_dict={}):
    """
    Render a template to PDF using xhtml2pdf.
    Returns HttpResponse with PDF content or None if PDF generation fails.
    """
    try:
        from xhtml2pdf import pisa
        
        template = get_template(template_src)
        html = template.render(context_dict)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
        
        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        else:
            logger.error(f"PDF generation error: {pdf.err}")
            return None
            
    except ImportError:
        logger.error("xhtml2pdf is not installed. Please install it with: pip install xhtml2pdf")
        return None
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return None 