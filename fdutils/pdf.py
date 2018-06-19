import io
# need pdfminer.six
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage


# originally from https://stackoverflow.com/a/44476759/1132603
def convert_pdf_to_txt(pdf_filepath, password='', encoding='utf-8'):
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    codec = encoding
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    with open(pdf_filepath, 'rb') as fp:
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        password = password
        maxpages = 0
        caching = True
        pagenos = set()

        for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages,
                                      password=password,
                                      caching=caching,
                                      check_extractable=True):
            interpreter.process_page(page)

        text = retstr.getvalue()

    device.close()
    retstr.close()
    return text
