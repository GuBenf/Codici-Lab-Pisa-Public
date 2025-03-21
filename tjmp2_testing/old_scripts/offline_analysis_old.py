import argparse
import glob
import os

from tjmonopix2.analysis import analysis, plotting


parser = argparse.ArgumentParser()
parser.add_argument('input_files', nargs='*', help='h5 files to analyze',
                    default=['output_data/module_0/chip_0/*.h5'], metavar='h5_file')
group = parser.add_mutually_exclusive_group()
group.add_argument('-i', action='store_true', help='Interpret h5 files that are not interpreted')
group.add_argument('-I', action='store_true', help='(Re)interpret all h5 files')
group = parser.add_mutually_exclusive_group()
group.add_argument('-p', action='store_true', help='Plot data from interpreted h5 files that have no PDF')
group.add_argument('-P', action='store_true', help='(Re)plot interpreted h5 files')
args = parser.parse_args()

if not any([args.i, args.I, args.p, args.P]):
    print("No action specified, nothing to do!")

input_files = []
interpreted_files = []
for x in args.input_files:
    for file in glob.glob(x):
        if 'interpreted' in os.path.basename(file):
            interpreted_files.append(file)
        else:
            input_files.append(file)
            interpreted_files.append(file.rsplit(".h5")[0] + "_interpreted.h5")

if args.i or args.I:
    for file in input_files:
        file_interpreted = file.rsplit(".h5")[0] + "_interpreted.h5"
        if args.I or not os.path.isfile(file_interpreted):
            print('Analyzing file:', file)
            with analysis.Analysis(raw_data_file=file) as a:
                a.analyze_data()

if args.p or args.P:
    for file in interpreted_files:
        pdf_file = file.rsplit(".h5")[0] + ".pdf"
        if os.path.isfile(file) and (args.P or not os.path.isfile(pdf_file)):
            print("Plotting:", file)
            with plotting.Plotting(analyzed_data_file=file) as p:
                p.create_standard_plots()
