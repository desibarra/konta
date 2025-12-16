try:
    import xhtml2pdf
    print('xhtml2pdf OK', getattr(xhtml2pdf, '__version__', 'unknown'))
except Exception as e:
    import traceback
    print('ERROR importing xhtml2pdf:', e)
    traceback.print_exc()

try:
    import lxml
    print('lxml OK', lxml.__version__)
except Exception as e:
    import traceback
    print('ERROR importing lxml:', e)
    traceback.print_exc()
