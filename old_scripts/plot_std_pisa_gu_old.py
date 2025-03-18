#!/usr/bin/env python3
"""Standard plots like hitmap and ToT histogram (HistOcc and HistToT not required)."""
import argparse
import glob
import os
import traceback
from itertools import product
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.cm
from matplotlib.colors import LogNorm
import matplotlib.pyplot as plt
import numpy as np
import tables as tb
from tqdm import tqdm
from plot_utils_pisa_gu import *


def main(input_files, overwrite=False, log_tot=False, output_file=None, ):
    if output_file is None:
        output_file = os.path.splitext(input_files[0])[0] + ".pdf"
    if os.path.isfile(output_file) and not overwrite:
        return

    # Prepare histograms
    counts2d = np.zeros((512, 512))
    tot1d = [np.zeros(128) for _ in range(len(FRONTENDS)+1)]
    tot1d_sel_pixel = [np.zeros(128) for _ in range(len(FRONTENDS)+1)]
    tot1d_single_hits = [np.zeros(128) for _ in range(len(FRONTENDS)+1)]
    tot2d = np.zeros((512, 512))
    counts2d16 = np.zeros((32, 32))
    tot2d16 = np.zeros((32, 32))
    matrix_dividers = [32,1]
    cfg = []
    tdac = []
    n_total_hits = 0
    thr_map = []
    scan_config = []
    enable_mask = []

    for input_file in tqdm(input_files, disable=len(input_files)<2):
        print("Processing", input_file)
        with tb.open_file(input_file) as f:
            cfg.append(get_config_dict(f))
            cf = int(cfg[0]['configuration_out.scan.scan_config.start_column'])
            cl = int(cfg[0]['configuration_out.scan.scan_config.stop_column'])
            rf = int(cfg[0]['configuration_out.scan.scan_config.start_row'])
            rl = int(cfg[0]['configuration_out.scan.scan_config.stop_row'])
            scan_config.append(cf)
            scan_config.append(cl)
            scan_config.append(rf)
            scan_config.append(rl)
            tdac.append(f.root.configuration_out.chip.masks.tdac[:])
            thr_map.append(f.root.ThresholdMap[:,:])
            enable_mask.append(f.root.configuration_out.chip.masks.enable[:])


            try:
                n_hits = f.root.Dut.shape[0]
            except tb.NoSuchNodeError:
                continue
            n_total_hits += n_hits

            # Process one chunk of data at a time
            csz = 2**24
            for i_first in tqdm(range(0, n_hits, csz), unit="chunk", disable=n_hits/csz<=1):
                i_last = min(n_hits, i_first + csz)

                # Load hits
                hits = f.root.Dut[i_first:i_last]
                with np.errstate(all='ignore'):
                    tot = (hits["te"] - hits["le"]) & 0x7f
                fe_masks = [(hits["col"] >= fc) & (hits["col"] <= lc) for fc, lc, _ in FRONTENDS]
                # fe_masks.append((hits["col"] > 470) & (hits["col"] < 472) & (hits["row"] > 150) & (hits["row"] < 152))
                #fe_masks.append(((hits["col"] == 470) & (hits["row"] == 470)) | ((hits["col"] == 150) & (hits["row"] == 150)))
                #sel_pixel_mask = ((hits["col"] == 470) & (hits["row"] == 300))
                # sel_pixel_mask = ((hits["col"] == 450) | (hits["col"] == 451))
                # sel_pixel_mask = ((hits["col"] > 298) & (hits["col"] < 305) & (hits["row"] > 255) & (hits["row"] < 331))
                sel_pixel_mask = ((hits["col"] > 287) & (hits["col"] < 295) & (hits["row"] > 287) & (hits["row"] < 295))
                single_hits_mask = is_single_hit_event(hits["timestamp"])

                counts2d_tmp, counts2d_edges, _ = np.histogram2d(
                    hits["col"], hits["row"], bins=[512, 512], range=[[0, 512], [0, 512]])


                counts2d += counts2d_tmp
                del counts2d_tmp

                for i, mask in enumerate(fe_masks):

                    tot1d_tmp, tot1d_edges = np.histogram(
                        tot[mask], bins=128, range=[-0.5, 127.5])
                    tot1d[i] += tot1d_tmp
                    tot1d_tmp, tot1d_edges = np.histogram(
                        tot[sel_pixel_mask & mask], bins=128, range=[-0.5, 127.5])
                    tot1d_sel_pixel[i] += tot1d_tmp
                    tot1d_tmp, tot1d_edges = np.histogram(
                        tot[single_hits_mask & mask], bins=128, range=[-0.5, 127.5])
                    tot1d_single_hits[i] += tot1d_tmp
                    del tot1d_tmp

                tot2d_tmp, tot2d_edges, _  = np.histogram2d(
                    hits["col"], hits["row"], bins=[512, 512], range=[[0, 512], [0, 512]],
                    weights=tot)
                tot2d += tot2d_tmp
                del tot2d_tmp

                counts2d16_tmp, edges16, _ = np.histogram2d(
                    hits["col"], hits["row"], bins=[32, 32], range=[[0, 512], [0, 512]])
                counts2d16 += counts2d16_tmp
                del counts2d16_tmp

                tot2d16_tmp, _, _  = np.histogram2d(
                    hits["col"], hits["row"], bins=[32, 32], range=[[0, 512], [0, 512]],
                    weights=tot)
                tot2d16 += tot2d16_tmp
                del tot2d16_tmp

                del hits, tot, fe_masks

    with PdfPages(output_file) as pdf:
        plt.figure(figsize=(6.4, 4.8))

        if len(input_files) > 1:
            plt.annotate(
                split_long_text(
                    "This file was generated by joining the following\n\n"
                    + "\n".join(input_files)
                    ), (0.5, 0.5), ha='center', va='center')
            plt.gca().set_axis_off()
            pdf.savefig(); plt.clf()

        for input_file, c, t, mk, th in zip(input_files, cfg, tdac, enable_mask, thr_map):
            draw_summary(input_file, c)
            pdf.savefig(); plt.clf()

            # TDAC map all matrix
            plt.axes((0.125, 0.11, 0.775, 0.72))
            nzc, nzr = np.nonzero(t)
            if not nzc.size:
                fc, lc, fr, lr = 0, 512, 0, 512
            else:
                fc, lc = nzc.min(), nzc.max() + 1
                fr, lr = nzr.min(), nzr.max() + 1

            del nzc, nzr

            plt.pcolormesh(np.arange(fc, lc + 1), np.arange(fr, lr + 1),
                           t[fc:lc, fr:lr].transpose(),
                           vmin=-0.5, vmax=7.5, cmap=TDAC_CMAP, rasterized=True)
            plt.xlabel("Column")
            plt.ylabel("Row")
            plt.title("Map of TDAC values (all matrix)")
            frontend_names_on_top()
            integer_ticks_colorbar().set_label("TDAC")
            pdf.savefig(); plt.clf()

            # TDAC map enabled matrix
            plt.axes((0.125, 0.11, 0.775, 0.72))
            fc = scan_config[0]
            lc = scan_config[1]
            fr = scan_config[2]
            lr = scan_config[3]

            plt.pcolormesh(np.arange(fc, lc + 1), np.arange(fr, lr + 1),
                           t[fc:lc, fr:lr].transpose(),
                           vmin=-0.5, vmax=7.5, cmap=TDAC_CMAP, rasterized=True)
            plt.xlabel("Column")
            plt.ylabel("Row")
            plt.title("Map of TDAC values (enabled matrix)")
            #frontend_names_on_top()
            integer_ticks_colorbar().set_label("TDAC")
            pdf.savefig(); plt.clf()

            # TDAC map regrouped
            plt.axes((0.125, 0.11, 0.775, 0.72))
            fc = scan_config[0]
            lc = scan_config[1]
            fr = scan_config[2]
            lr = scan_config[3]
            ddx = matrix_dividers[0]
            ddy = matrix_dividers[1]
            m_blocks,m_blocks_masked = get_block_matrix(t[0:512, 0:512],dx = ddx,dy=ddy,mask=mk[0:512, 0:512])
            # m_blocks = get_block_matrix(t[fc:lc, fr:lr],dx = ddx,dy=ddy)
            x_ti = np.arange(0+ddx/2, t.shape[1]+ddx/2, ddx)  # X axis values
            y_ti = np.arange(0+ddy/2, t.shape[0]+ddy/2, ddy)   # Y axis values

            plt.pcolormesh(x_ti, y_ti,
                           m_blocks_masked,
                           vmin=-0.5, vmax=7.5, cmap=TDAC_CMAP, rasterized=True)
            plt.xlabel("Column")
            plt.ylabel("Row")
            plt.title("Map of mean TDAC values")
            frontend_names_on_top()
            integer_ticks_colorbar().set_label("TDAC")
            pdf.savefig(); plt.clf()
            del x_ti,y_ti,m_blocks,m_blocks_masked

            # TDAC full row projection
            plt.axes((0.125, 0.11, 0.775, 0.72))
            nzc, nzr = np.nonzero(t)
            if not nzc.size:
                fc, lc, fr, lr = 0, 512, 0, 512
            else:
                fc, lc = nzc.min(), nzc.max() + 1
                fr, lr = nzr.min(), nzr.max() + 1

            del nzc, nzr
            t_dac_rows = [np.mean(t[:,i]) for i in range(lr)]
            indx = [i for i in range(lr)]
            plt.plot(indx,t_dac_rows)
            plt.xlabel("Row")
            plt.ylabel("Mean TDAC")
            plt.grid()
            plt.title("Mean of TDAC values per row")
            #frontend_names_on_top()
            # integer_ticks_colorbar().set_label("TDAC")
            pdf.savefig(); plt.clf()
            del t_dac_rows,indx

            # TDAC selected flavor row projection
            for fc, lc, name in FRONTENDS:
                plt.axes((0.125, 0.11, 0.775, 0.72))
                t_dac_rows = [np.mean(t[fc:lc,i]) for i in range(lr)]
                indx = [i for i in range(lr)]
                plt.plot(indx,t_dac_rows)
                plt.xlabel("Row")
                plt.ylabel("Mean TDAC")
                plt.grid()
                plt.title("Mean of TDAC values per row - "+name)
                #frontend_names_on_top()
                # integer_ticks_colorbar().set_label("TDAC")
                pdf.savefig(); plt.clf()
                del t_dac_rows,indx

            # TDAC partial row projection
            plt.axes((0.125, 0.11, 0.775, 0.72))
            nzc, nzr = np.nonzero(t)
            if not nzc.size:
                fc, lc, fr, lr = 0, 512, 0, 512
            else:
                fc, lc = nzc.min(), nzc.max() + 1
                fr, lr = nzr.min(), nzr.max() + 1
            del nzc, nzr

            ddx = matrix_dividers[0]
            ddy = matrix_dividers[1]

            # t_blocks = get_block_matrix(t[fc:lc, fr:lr],dx = ddx,dy=ddy).transpose()
            t_blocks,t_blocks_masked = get_block_matrix(t[0:512, 0:512],dx = ddx,dy=ddy,mask=mk[0:512, 0:512])
            t_blocks_masked = t_blocks_masked.transpose()
            # t_blocks,_ = get_block_matrix(t[0:512, 0:512],dx = ddx,dy=ddy)
            indx_col = [i for i in range(len(t_blocks_masked))]
            indx = [i for i in range(len(t_blocks_masked[0]))]
            # t_blocks_masked_m = [pp for pp in t_blocks_masked]
            # plt.plot(indx,t_blocks_masked[0])
            for j,p_col in enumerate(t_blocks_masked):
                non_zero = [k for k in p_col if k != 0]
                if len(non_zero)>0:
                    plt.plot(indx,p_col,label=f"{ddx} cols group n.: {j}")

            plt.xlabel(f"{ddy} x Row")
            plt.ylabel("Mean TDAC")
            plt.grid()
            plt.title(f"Mean of TDAC values for a {ddx}x{ddy} block")
            plt.legend(loc="best")
            #frontend_names_on_top()
            # integer_ticks_colorbar().set_label("TDAC")
            pdf.savefig(); plt.clf()
            del indx_col,indx, t_blocks, t_blocks_masked

            # ------------------------------------------


            # Threshold map all matrix
            plt.axes((0.125, 0.11, 0.775, 0.72))
            nzc, nzr = np.nonzero(th)
            if not nzc.size:
                fc, lc, fr, lr = 0, 512, 0, 512
            else:
                fc, lc = nzc.min(), nzc.max() + 1
                fr, lr = nzr.min(), nzr.max() + 1

            del nzc, nzr

            plt.pcolormesh(np.arange(fc, lc + 1), np.arange(fr, lr + 1),
                           th[fc:lc, fr:lr].transpose(),
                           vmin=22, vmax=36, cmap="viridis", rasterized=True)
            plt.xlabel("Column")
            plt.ylabel("Row")
            plt.title("Map of THR values (all matrix)")
            frontend_names_on_top()
            integer_ticks_colorbar().set_label("THR")
            pdf.savefig(); plt.clf()

            # THR map enabled matrix
            plt.axes((0.125, 0.11, 0.775, 0.72))
            fc = scan_config[0]
            lc = scan_config[1]
            fr = scan_config[2]
            lr = scan_config[3]

            plt.pcolormesh(np.arange(fc, lc + 1), np.arange(fr, lr + 1),
                           th[fc:lc, fr:lr].transpose(),
                           vmin=22, vmax=36, cmap="viridis", rasterized=True)

            plt.xlabel("Column")
            plt.ylabel("Row")
            plt.title("Map of THR values (enabled matrix)")
            #frontend_names_on_top()
            integer_ticks_colorbar().set_label("THR")
            pdf.savefig(); plt.clf()

            # THR map regrouped
            plt.axes((0.125, 0.11, 0.775, 0.72))
            fc = scan_config[0]
            lc = scan_config[1]
            fr = scan_config[2]
            lr = scan_config[3]
            ddx = matrix_dividers[0]
            ddy = matrix_dividers[1]
            m_blocks,m_blocks_masked = get_block_matrix(th[0:512, 0:512],dx = ddx,dy=ddy,mask=mk[0:512, 0:512])
            # m_blocks = get_block_matrix(t[fc:lc, fr:lr],dx = ddx,dy=ddy)
            x_ti = np.arange(0+ddx/2, th.shape[1]+ddx/2, ddx)  # X axis values
            y_ti = np.arange(0+ddy/2, th.shape[0]+ddy/2, ddy)   # Y axis values
            plt.pcolormesh(x_ti, y_ti,
                           m_blocks_masked,
                           vmin=22, vmax=36, cmap="viridis", rasterized=True)
            plt.xlabel("Column")
            plt.ylabel("Row")
            plt.title("Map of mean THR values")
            frontend_names_on_top()
            integer_ticks_colorbar().set_label("THR")
            pdf.savefig(); plt.clf()
            del x_ti,y_ti, m_blocks,m_blocks_masked

            # THR full row projection
            plt.axes((0.125, 0.11, 0.775, 0.72))
            nzc, nzr = np.nonzero(th)
            if not nzc.size:
                fc, lc, fr, lr = 0, 512, 0, 512
            else:
                fc, lc = nzc.min(), nzc.max() + 1
                fr, lr = nzr.min(), nzr.max() + 1

            del nzc, nzr
            thr_rows = [np.mean(th[:,i]) for i in range(lr)]
            indx = [i for i in range(lr)]
            plt.plot(indx,thr_rows)
            plt.xlabel("Row")
            plt.ylabel("Mean THR")
            plt.grid()
            plt.title("Mean of THR values per row")
            #frontend_names_on_top()
            # integer_ticks_colorbar().set_label("TDAC")
            pdf.savefig(); plt.clf()
            del thr_rows,indx

            # THR partial row projection
            plt.axes((0.125, 0.11, 0.775, 0.72))
            nzc, nzr = np.nonzero(th)
            if not nzc.size:
                fc, lc, fr, lr = 0, 512, 0, 512
            else:
                fc, lc = nzc.min(), nzc.max() + 1
                fr, lr = nzr.min(), nzr.max() + 1
            del nzc, nzr

            ddx = matrix_dividers[0]
            ddy = matrix_dividers[1]

            # t_blocks = get_block_matrix(t[fc:lc, fr:lr],dx = ddx,dy=ddy).transpose()
            t_blocks,t_blocks_masked = get_block_matrix(th[0:512, 0:512],dx = ddx,dy=ddy,mask=mk[0:512, 0:512])
            t_blocks_masked = t_blocks_masked.transpose()
            # t_blocks,_ = get_block_matrix(t[0:512, 0:512],dx = ddx,dy=ddy)
            indx_col = [i for i in range(len(t_blocks_masked))]
            indx = [i for i in range(len(t_blocks_masked[0]))]
            # t_blocks_masked_m = [pp for pp in t_blocks_masked]
            # plt.plot(indx,t_blocks_masked[0])
            means = []
            for j,p_col in enumerate(t_blocks_masked):
                non_zero = [k for k in p_col if k != 0]
                if len(non_zero)>0:
                    plt.plot(indx,p_col,label=f"{ddx} cols group n.: {j}")
                    means.append(np.mean(p_col))

                # plt.plot(indx,p_col,label=f"col n.: {j}")
            plt.xlabel(f"{ddy} x Row")
            plt.ylabel("Mean THR")
            plt.ylim(max(means)-2,max(means)+2)
            # plt.xlim(0,100)
            plt.grid()
            plt.title(f"Mean of THR values for a {ddx}x{ddy} block")
            plt.legend(loc="best")
            #frontend_names_on_top()
            # integer_ticks_colorbar().set_label("TDAC")
            pdf.savefig(); plt.clf()
            del indx_col,indx, t_blocks, t_blocks_masked


        # print("Summary")

        if n_total_hits == 0:
            plt.annotate("No hits recorded!", (0.5, 0.5), ha='center', va='center')
            plt.gca().set_axis_off()
            pdf.savefig(); plt.clf()
            return

        # Histogram of hits per pixel
        m = np.quantile(counts2d[counts2d > 0], 0.99) * 10.5 if np.any(counts2d > 0) else 1
        bins = 100 if m > 200 else int(max(m, 5))
        for fc, lc, name in FRONTENDS:
            plt.hist(counts2d[fc:lc+1,:].reshape(-1), label=name, histtype='step',
                     bins=bins, range=[0.5, max(m, 5) + 0.5])
        plt.title("Hits per pixel")
        plt.xlabel("Number of hits")
        plt.ylabel("Pixels / bin")
        plt.ylim(1., max(h.max() for h in counts2d) * 10000)
        #plt.ylim(1., 1e8)
        plt.yscale("log")
        plt.grid(which='both',axis='y')
        set_integer_ticks(plt.gca().xaxis)
        #set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
        plt.legend()
        pdf.savefig(); plt.clf()
        # print("Hits hist")



        # Histogram of ToT for selected pixels
        for (_, _, name), hist in zip(FRONTENDS, tot1d_sel_pixel):
            plt.step((tot1d_edges[1:] + tot1d_edges[:-1]) / 2,
                     hist, where='mid', label=name)
        #print(tot1d[2])
        plt.title("ToT selected pixels")
        plt.xlabel("ToT [25 ns]")
        plt.ylabel("Hits / bin")
        plt.xlim(0, 30)
        # plt.xlim(0, 130)
        #plt.ylim(0, max(h[10:].max() for h in tot1d) * 1.2)
        plt.minorticks_on()
        plt.grid(which='major',axis='both')
        if log_tot:
            # plt.ylim(0.9, max(h[10:120].max() for h in tot1d) * 1.2)
            plt.ylim(0.1, max(h.max() for h in tot1d) * 1.2)
            plt.yscale('log')
            set_integer_ticks(plt.gca().xaxis)
        else:
            #plt.ylim(0, max(h[10:120].max() for h in tot1d) * 1.2)
            set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
        plt.legend()
        pdf.savefig(); plt.clf()




        # Histogram of ToT
        for (_, _, name), hist in zip(FRONTENDS, tot1d):
            plt.step((tot1d_edges[1:] + tot1d_edges[:-1]) / 2,
                     hist, where='mid', label=name)
        plt.title("ToT")
        plt.xlabel("ToT [25 ns]")
        plt.ylabel("Hits / bin")
        plt.xlim(0, 30)
        # plt.xlim(0, 130)
        #plt.ylim(0, max(h[10:].max() for h in tot1d) * 1.2)
        plt.minorticks_on()
        plt.grid(which='major',axis='both')
        if log_tot:
            # plt.ylim(0.9, max(h[10:120].max() for h in tot1d) * 1.2)
            plt.ylim(0.1, max(h.max() for h in tot1d) * 1.2)
            plt.yscale('log')
            set_integer_ticks(plt.gca().xaxis)
        else:
            #plt.ylim(0, max(h[10:120].max() for h in tot1d) * 1.2)
            set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
        plt.legend()
        pdf.savefig(); plt.clf()
        # print("ToT Hist")

        # Histogram of ToT (single hits)
        for (_, _, name), hist in zip(FRONTENDS, tot1d_single_hits):
            plt.step((tot1d_edges[1:] + tot1d_edges[:-1]) / 2,
                     hist, where='mid', label=name)
        plt.title("ToT (isolated hits only)")
        plt.xlabel("ToT [25 ns]")
        plt.ylabel("Hits / bin")
        plt.grid(which='both',axis='both')
        plt.xlim(0, 30)
        if log_tot:
            plt.yscale('log')
            set_integer_ticks(plt.gca().xaxis)
        else:
            set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
        plt.legend()
        pdf.savefig(); plt.clf()
        # print("ToT Hist")

        # Hit map
        cmap = matplotlib.cm.get_cmap("viridis").copy()
        cmap.set_over("r")
        plt.pcolormesh(counts2d_edges, counts2d_edges, counts2d.transpose(),
                       vmin=0, vmax=300, cmap=cmap, rasterized=True)  # Necessary for quick save and view in PDF
         #           cmap=cmap, rasterized=True, norm=LogNorm())  # Necessary for quick save and view in PDF
                    #  cmap=cmap, rasterized=True)  # Necessary for quick save and view in PDF
        plt.title("Hit map")
        plt.xlabel("Col")
        plt.ylabel("Row")
        cb = integer_ticks_colorbar()
        cb.set_label("Hits / pixel")
        set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
        frontend_names_on_top()
        pdf.savefig(); plt.clf()

        ZOOM_STEP = 64
        for i, j in product(range(0, 512, ZOOM_STEP), range(0, 512, ZOOM_STEP)):
            i1 = min(i+ZOOM_STEP, 512)
            j1 = min(j+ZOOM_STEP, 512)
            if not np.any(counts2d[i:i1,j:j1]):
                continue
            plt.pcolormesh(counts2d_edges[i:i1+1], counts2d_edges[j:j1+1], counts2d[i:i1,j:j1].transpose(),
                           vmin=0, vmax=300, cmap=cmap, rasterized=True)  # Necessary for quick save and view in PDF
            #              rasterized=True, norm=LogNorm())  # Necessary for quick save and view in PDF
                                        #  rasterized=True)  # Necessary for quick save and view in PDF
            plt.title("Hit map (subregion)")
            plt.xlabel("Col")
            plt.ylabel("Row")
            cb = integer_ticks_colorbar()
            cb.set_label("Hits / pixel")
            set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
            frontend_names_on_top()
            plt.xlim(i, i1)
            plt.ylim(j, j1)
            pdf.savefig(); plt.clf()
        # print("Hitmap")

        # Map of the average ToT tst
        with np.errstate(all='ignore'):
            totavg = tot2d / counts2d
        plt.pcolormesh(tot2d_edges, tot2d_edges, totavg.transpose(),
                       vmin=0.5, vmax=70.5, rasterized=True)  # Necessary for quick save and view in PDF
        plt.title("Average ToT map")
        plt.xlabel("Col")
        plt.ylabel("Row")
        plt.grid()
        cb = integer_ticks_colorbar()
        cb.set_label("ToT [25 ns]")
        set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
        frontend_names_on_top()
        pdf.savefig(); plt.clf()

        for i, j in product(range(0, 512, ZOOM_STEP), range(0, 512, ZOOM_STEP)):
            i1 = min(i+ZOOM_STEP, 512)
            j1 = min(j+ZOOM_STEP, 512)
            if not np.any(counts2d[i:i1,j:j1]):
                continue
            plt.pcolormesh(tot2d_edges[i:i1+1], tot2d_edges[j:j1+1], totavg[i:i1,j:j1].transpose(),
                           vmin=0.5, vmax=70.5, rasterized=True)  # Necessary for quick save and view in PDF
            plt.title("Average ToT map (subregion)")
            plt.xlabel("Col")
            plt.ylabel("Row")
            plt.grid()
            cb = integer_ticks_colorbar()
            cb.set_label("ToT [25 ns]")
            set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
            frontend_names_on_top()
            plt.xlim(i, i1)
            plt.ylim(j, j1)
            pdf.savefig(); plt.clf()
        # print("ToT map")

        # Noisy pixels
        if all(c.get("configuration_out.scan.run_config.scan_id") == "source_scan" for c in cfg):
            MAX_RATE = 0.001  # Above this rate [Hz] pixels are marked noisy
            scan_time = 10
            for i, c in enumerate(cfg):
                try:
                    scan_time += float(c["configuration_out.scan.scan_config.scan_time"])
                except Exception:
                    print(f"WARNING: could not determine scan time from {input_files[i]}")
            max_hits = scan_time * MAX_RATE
            mask = counts2d > max_hits
            plt.axes((0.125, 0.11, 0.775, 0.72))
            plt.pcolormesh(counts2d_edges, counts2d_edges, 1 * mask.transpose(),
                           vmin=0, vmax=1, rasterized=True)  # Necessary for quick save and view in PDF
            plt.suptitle("Noisy pixels in yellow (ignore this plot if source was used)")
            plt.title(f"Noisy means rate > {MAX_RATE:.3g} Hz")
            plt.xlabel("Col")
            plt.ylabel("Row")
            set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
            frontend_names_on_top()
            pdf.savefig(); plt.clf()

            if np.count_nonzero(mask):
                noisy_list = np.argwhere(mask)
                noisy_indices = np.nonzero(mask)
                srt = np.argsort(-counts2d[noisy_indices])
                noisy_indices = tuple(x[srt] for x in noisy_indices)
                noisy_list = noisy_list[srt]
                mi = min(len(noisy_list), 20)
                tmp = "\n".join(
                    ",    ".join(f"({a}, {b}) = {float(c)/scan_time:.3g}" for (a, b), c in g)
                    for g in groupwise(zip(noisy_list[:mi], counts2d[tuple(x[:mi] for x in noisy_indices)]), 1))
                plt.annotate(
                    split_long_text(
                        "Noisiest pixels (col, row) = rate [Hz]\n"
                        f"{tmp}"
                        f'{", ..." if len(noisy_list) > mi else ""}'
                        f"\nTotal = {len(noisy_list)} pixels"
                    ), (0.5, 0.5), ha='center', va='center')
                output_file_txt = os.path.splitext(input_files[0])[0]
                with open(output_file_txt + "_noisy_pixels_rate.txt", "w") as f1:
                    print("[" + ", ".join(f'"{int(a)}, {int(b)}"' for a, b in noisy_list) + "]", file=f1)
            else:
                plt.annotate("No noisy pixel found.", (0.5, 0.5), ha='center', va='center')
            plt.gca().set_axis_off()
            pdf.savefig(); plt.clf()
        # print("Noisy")

        # Source positioning (16x16 pixels blocks histogram)
        m = np.quantile(counts2d16[counts2d16 > 0], 0.99) * 1.2 if np.any(counts2d > 0) else 1
        plt.pcolormesh(edges16, edges16, counts2d16.transpose(), vmin=0, vmax=m,
                       cmap=cmap, rasterized=True)  # Necessary for quick save and view in PDF
        plt.title("Hit map in 16x16 regions for source positioning")
        plt.xlabel("Col")
        plt.ylabel("Row")
        cb = plt.colorbar()
        cb.set_label("Avg. hits / 16x16 region (red = out of scale)")
        set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
        frontend_names_on_top()
        pdf.savefig(); plt.clf()
        # print("Source")

        # Coarse (16x16 pixel blocks) map of the average ToT
        with np.errstate(all='ignore'):
            totavg16 = tot2d16 / counts2d16
        plt.pcolormesh(edges16, edges16, totavg16.transpose(),
                       vmin=-0.5, vmax=60.5, rasterized=True)  # Necessary for quick save and view in PDF
        plt.title("Average ToT map in 16x16 regions")
        plt.xlabel("Col")
        plt.ylabel("Row")
        cb = plt.colorbar()
        cb.set_label("ToT [25 ns]")
        set_integer_ticks(plt.gca().xaxis, plt.gca().yaxis)
        frontend_names_on_top()
        pdf.savefig(); plt.clf()

        plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_file", nargs="*",
        help="The _interpreted.h5 file(s). If not given, looks in output_data/module_0/chip_0.")
    parser.add_argument("-f", "--overwrite", action="store_true",
                        help="Overwrite plots when already present.")
    parser.add_argument("-j", "--join", metavar="OUTPUT_FILE.PDF", default=None,
                        help="Join all input files and put results in the given PDF.")
    parser.add_argument("--log-tot", action="store_true",
                        help="Use log scale for ToT.")
    args = parser.parse_args()

    files = []
    if args.input_file:  # If anything was given on the command line
        for pattern in args.input_file:
            files.extend(glob.glob(pattern, recursive=True))
    else:
        files.extend(glob.glob("output_data/module_0_guglielmo/chip_0/*_interpreted.h5"))
    files.sort()

    if args.join is None:
        for fp in tqdm(files):
            try:
                main([fp], args.overwrite, args.log_tot)
            except Exception:
                print(traceback.format_exc())
    else:
        main(files, args.overwrite, args.log_tot, args.join)
