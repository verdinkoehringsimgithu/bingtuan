"""Run the same native confirmation protocol with separately versioned inputs."""
from pathlib import Path
import confirm_paths as confirmation

# This is a new process and new output tree. The original input files,
# original selected policy and its running validation remain untouched.
confirmation.lab.OUT=Path(__file__).resolve().parent/'results/refined'
confirmation.OUT=confirmation.lab.OUT/'confirmation'

if __name__=='__main__':confirmation.main()
