from PyPDF4 import PdfFileMerger
import pdfkit

from pathlib import Path
from natsort import natsorted
import shutil

from argparse import ArgumentParser


def merge_pdf_files(pdf_files, output_path):
    merger = PdfFileMerger()
    for file in pdf_files:
        merger.append(file)
    merger.write(output_path)
    merger.close()


def convert_html_to_pdf(html_files, output_path):
    pdfkit.from_file(html_files, output_path)


def get_files_from_folder(folder_path):
    files = natsorted(list(folder_path.glob("*")))
    return files[0].suffix, [str(f) for f in files]


def clean_dir(folder_path):
    shutil.rmtree(folder_path)
    print("\nArquivos convertidos com sucesso!")


parser = ArgumentParser()
parser.add_argument("-p", "--path", type=str, default = None, help="caminho para a pasta")
options = parser.parse_args()

if options.path:
    folder_path = options.path
else:
    folder_path = input("\n Insira o caminho para a pasta: ")

folder_path = Path(folder_path.strip())
parents = Path(folder_path.parent)
output_pdf = str(parents.joinpath(Path(folder_path.with_suffix('.pdf')).name))

suffix, f_list = get_files_from_folder(folder_path)
if suffix == ".pdf":
    merge_pdf_files(f_list, output_pdf)
    clean_dir(folder_path)
elif suffix == ".html":
    convert_html_to_pdf(f_list, output_pdf)
    clean_dir(folder_path)
else:
    print("Nenhum arquivo para converter.")