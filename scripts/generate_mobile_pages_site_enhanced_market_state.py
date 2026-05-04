from pathlib import Path
import runpy, sys
if __name__ == '__main__':
    script = Path(__file__).with_name('generate_mobile_pages_site_professional_dashboard.py')
    sys.argv = [str(script)] + sys.argv[1:]
    runpy.run_path(str(script), run_name='__main__')
