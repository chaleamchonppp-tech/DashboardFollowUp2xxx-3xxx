"""Build the static GitHub Pages site without bundling any database or credentials."""
import argparse
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'_site'));args=parser.parse_args()
    output=Path(args.output).resolve()
    if output == ROOT or ROOT in output.parents and output.name != '_site':
        raise SystemExit('Use _site or an output directory outside the repository')
    output.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'static',output,dirs_exist_ok=True)
    (output/'data').mkdir(exist_ok=True)
    for name in ('seed.json','reference.json'):shutil.copy2(ROOT/'data'/name,output/'data'/name)
    (output/'.nojekyll').touch()
    print('Static site built:',output)
