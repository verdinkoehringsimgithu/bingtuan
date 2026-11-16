"""Independent macro scanner. The same configuration powers the complete study."""
import sys
from run_research import main
if __name__=="__main__":
    if "--stop-after" not in sys.argv: sys.argv.extend(["--stop-after","scan"])
    main()
