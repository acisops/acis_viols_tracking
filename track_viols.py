import matplotlib as mpl
mpl.use('Agg')
mpl.rcParams.update({'figure.max_open_warning': 0})
import matplotlib.pyplot as plt
plt.ioff()
import acispy
from kadi import events
import numpy as np
from Chandra.Time import secs2date, DateTime, date2secs
import jinja2
import os
import re
from datetime import datetime
import glob
from collections import defaultdict, OrderedDict
from Ska.Matplotlib import cxctime2plotdate
from matplotlib.dates import num2date, DateFormatter, date2num
import json
from email.mime.text import MIMEText
from subprocess import Popen, PIPE
import json
from acispy.utils import mylog
mylog.setLevel(40)

colors = {"Planning": "green",
          "Yellow": "gold",
          "ACIS-I": "C0",
          "ACIS-S": "C1"}

f = open("limits.json", "r")
limits = json.load(f)
f.close()
temps = list(limits.keys())


class TrackACISViols(object):
    def __init__(self, end=None):
        now = datetime.utcnow()
        if end is None:
            end = now
        elif isinstance(end, int):
            if now.year == end:
                end = now
            else:
                end = datetime(end, 12, 31, 23, 59, 59)
        else:
            end = datetime.strptime(end, "%Y:%j:%H:%M:%S")
        begin = datetime(end.year, 1, 1)
        datestart = begin.strftime("%Y:%j:%H:%M:%S")
        datestop = end.strftime("%Y:%j:%H:%M:%S")
        self.year = end.year
        print("Tracking violations for the year %s." % self.year)
        self.now = now
        self.ds = acispy.TelemData(datestart, datestop, temps, stat="5min")
        self.obsids = events.obsids.filter(start=datestart, stop=datestop)

    def find_viols(self, msid):
        if msid == "fptemp_11":
            viols, num_viols = self._find_fptemp_viols(msid)
        else:
            viols, num_viols = self._find_viols(msid)
        plot_data = self._make_plots(msid, viols)

        if msid == "fptemp_11":
            which = msid+"_"
        else:
            which = ""
        viols_template_file = 'viols_%stemplate.rst' % which

        viols_template = open(os.path.join('templates', viols_template_file)).read()
        viols_template = re.sub(r' %}\n', ' %}', viols_template)

        context = {"viols": viols,
                   "num_viols": num_viols,
                   "year": self.year,
                   "msid": msid.upper()}

        year_dir = os.path.join("source", str(self.year))
        if not os.path.exists(year_dir):
            os.mkdir(year_dir)
        outfile = os.path.join(year_dir, "viols_%s.rst" % msid)

        template = jinja2.Template(viols_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))

        return viols, plot_data

    def _find_viols(self, msid):
        num_viols = {"Planning": 0, "Yellow": 0}
        viols = []
        msid_times = self.ds[msid].times.value
        msid_vals = self.ds[msid].value
        for ltype in ["Planning", "Yellow"]:
            limit_vals = np.zeros(msid_vals.size)
            for lim in limits[msid]:
                lim_start = date2secs(lim["start"])
                limit_vals[msid_times >= lim_start] = lim[ltype]
            bad = np.concatenate(([False], msid_vals >= limit_vals, [False]))
            changes = np.flatnonzero(bad[1:] != bad[:-1]).reshape(-1, 2)
            for change in changes:
                duration = msid_times[change[1] - 1] - msid_times[change[0]]
                if duration < 10.0:
                    continue
                viol = {'viol_tstart': msid_times[change[0]],
                        'viol_tstop': msid_times[change[1] - 1],
                        'maxtemp': msid_vals[change[0]:change[1]].max(),
                        'limit': limit_vals[change[0]],
                        'type': ltype}
                viol["viol_datestart"] = secs2date(viol["viol_tstart"])
                viol["viol_datestop"] = secs2date(viol["viol_tstop"])
                viol["duration"] = (viol["viol_tstop"]-viol["viol_tstart"])/1000.0
                viols.append(viol)
                num_viols[ltype] += 1
        return viols, num_viols

    def _find_fptemp_viols(self, msid):
        num_viols = {"ACIS_I": 0, "ACIS_S": 0}
        viols = []
        msid_times = self.ds[msid].times.value
        msid_vals = self.ds[msid].value
        for obsid in self.obsids:
            if obsid.obsid < 38000:
                when_clocking = ((self.ds["clocking"] == 1) &
                                 (self.ds["tstart"].value >= obsid.tstart) &
                                 (self.ds["tstop"].value <= obsid.tstop))
                instr = self.ds["instrument"][when_clocking]
                if len(instr.value) < 1 or np.char.startswith(instr.value, "HRC").any():
                    continue
                if not np.all(instr == instr[0]):
                    print(instr)
                    raise RuntimeError("OOPS!")
                tbegin_clock = self.ds["tstart"][when_clocking][0].value
                tend_clock = self.ds["tstop"][when_clocking][-1].value
                idxs = np.logical_and(msid_times >= tbegin_clock, msid_times <= tend_clock)
                this_limit = None
                for lim in limits[msid]:
                    lim_start = date2secs(lim["start"])
                    if tbegin_clock >= lim_start:
                        this_limit = lim[instr[0]]
                bad = (msid_vals[idxs] > this_limit) & ~(msid_vals[idxs] > -90.0)
                bad = np.concatenate(([False], bad, [False]))
                time_data = msid_times[idxs]
                if np.any(bad):
                    changes = np.flatnonzero(bad[1:] != bad[:-1]).reshape(-1, 2)
                    for change in changes:
                        duration = time_data[change[1] - 1] - time_data[change[0]]
                        if duration < 10.0:
                            continue
                        viol = {"obsid": obsid.obsid,
                                "limit": this_limit,
                                "tstart": tbegin_clock,
                                "tstop": tend_clock,
                                "datestart": secs2date(tbegin_clock),
                                "datestop": secs2date(tend_clock),
                                "type": instr[0],
                                "time_data": msid_times[idxs],
                                "temp_data": msid_vals[idxs]}
                        viol["maxtemp"] = viol["temp_data"][change[0]:change[1]].max()
                        viol['viol_tstart'] = viol["time_data"][change[0]]
                        viol['viol_tstop'] = viol["time_data"][change[1] - 1]
                        viol["viol_datestart"] = secs2date(viol["viol_tstart"])
                        viol["viol_datestop"] = secs2date(viol["viol_tstop"])
                        viol["duration"] = (viol["viol_tstop"]-viol["viol_tstart"])/1000.0
                        viols.append(viol)
                        num_viols[instr[0].replace("-","_")] += 1
        return viols, num_viols

    def _make_plots(self, msid, viols):
        lim_types = list(limits[msid][0].keys())
        lim_types.remove("start")
        doys = defaultdict(list)
        diffs = defaultdict(list)
        durations = defaultdict(list)
        if len(viols) == 0:
            return doys, diffs, durations
        for i, viol in enumerate(viols):
            doy = datetime.strptime(viol["viol_datestop"].split(".")[0],
                                    "%Y:%j:%H:%M:%S").timetuple().tm_yday
            dp = acispy.DatePlot(self.ds, msid, figsize=(11, 8), field2=("states", "pitch"))
            doys[viol["type"]].append(doy)
            diffs[viol["type"]].append(viol["maxtemp"]-viol["limit"])
            durations[viol["type"]].append(viol["duration"])
            if msid == "fptemp_11":
                otime = viol["tstop"]-viol["tstart"]
                plot_tbegin = viol["tstart"]-0.5*otime
                plot_tend = viol["tstop"]+0.5*otime
                dp.add_vline(secs2date(viol['tstart']), color='orange')
                dp.add_vline(secs2date(viol['tstop']), color='orange')
                ymin, ymax = dp.ax.get_ylim()
                ymid = 0.5*(ymin+ymax)
                dp.add_text(secs2date(viol['tstart']+0.05*otime), ymid,
                            'BEGIN CLOCKING', rotation='vertical', color='orange')
                dp.add_text(secs2date(viol['tstop']+0.05*otime), ymid,
                            'END CLOCKING', rotation='vertical', color='orange')
            else:
                otime = viol["viol_tstop"]-viol["viol_tstart"]
                plot_tbegin = viol["viol_tstart"]-otime
                plot_tend = viol["viol_tstop"]+otime
            dp.add_hline(viol['limit'], ls='--')
            dp.set_xlim(secs2date(plot_tbegin), secs2date(plot_tend))
            dp.set_ylabel(r"$\mathrm{Temperature\ (^\circ{C})}$")
            title = "Violation start: {}\n" \
                    "Violation stop: {}\n" \
                    "Violation duration: {:.2f} ks".format(viol["viol_datestart"],
                                                           viol["viol_datestop"],
                                                           viol["duration"])
            if msid == "fptemp_11":
                title += ", OBSID: {}".format(viol["obsid"])
            dp.set_title(title)
            plot_idxs = np.logical_and(dp.times["msids", msid].value >= plot_tbegin,
                                       dp.times["msids", msid].value <= plot_tend)
            ymax = dp.y["msids", msid][plot_idxs].value.max()+1.0
            ymin = dp.y["msids", msid][plot_idxs].value.min()-1.0
            dp.set_ylim(ymin, ymax)
            fn = "%s_%s_%d.png" % (msid, self.year, i)
            if not os.path.exists("source/_static"):
                os.mkdir("source/_static")
            dp.savefig(os.path.join("source/_static", fn))
            viol["plot"] = os.path.join("..", "_static", fn)
        plt.rc("font", size=14)
        fig = plt.figure(figsize=(16, 5))
        ax = fig.add_subplot(131)
        if self.year == self.now.year:
            max_doys = self.now.timetuple().tm_yday
        else:
            max_doys = 365
            if int(self.year) % 4 == 0:
                max_doys += 1
        bins = np.linspace(1, max_doys, min(max_doys // 7, 1))
        for k in lim_types:
            ax.hist(doys[k], bins=bins, cumulative=True, histtype='step',
                    lw=3, label=k, color=colors[k])
        ax.set_xlim(1, max_doys)
        ax.set_xlabel("DOY")
        ax.set_ylabel("# of violations")
        ax.legend(loc=2)
        ax2 = fig.add_subplot(132)
        for k in doys:
            if len(doys[k]) > 0:
                ax2.scatter(doys[k], diffs[k], marker='x',
                            color=colors[k])
        ax2.set_xlim(1, max_doys)
        ax2.set_xlabel("DOY")
        ax2.set_ylabel(r"$\mathrm{\Delta{T}\ (^\circ{C})}$")
        _, ymax = ax2.get_ylim()
        ax2.set_ylim(0.0, max(1.5, ymax))
        ax3 = fig.add_subplot(133)
        for k in doys:
            if len(doys[k]) > 0:
                ax3.scatter(doys[k], durations[k], marker='x',
                            color=colors[k])
        ax3.set_xlim(1, max_doys)
        ax3.set_xlabel("DOY")
        ax3.set_ylabel("Duration (ks)")
        _, ymax = ax3.get_ylim()
        ax3.set_ylim(0.0, max(10.0, ymax))
        fig.subplots_adjust(wspace=0.25)
        fig.savefig(os.path.join("source", "_static",
                                 "hist_%s_%s.png" % (msid, self.year)))
        plt.close("all")
        return doys, diffs, durations

    def check_for_new_viols(self, viols):
        # Check to see if there are any new violations
        # since the last time we looked
        if self.year == self.now.year:
            if os.path.exists("last_viols.json"):
                f = open("last_viols.json", "r")
                last_known_viols = json.load(f)
                f.close()
                for msid in temps:
                    if len(viols[msid]) == 0 or last_known_viols[msid] is None:
                        continue
                    old_time = date2secs(last_known_viols[msid])
                    vtimes = np.array([viol["viol_tstop"] for viol in viols[msid]])
                    vtypes = np.array([viol["type"] for viol in viols[msid]])
                    # Buffer this by ~100 s to avoid spurious
                    # reports due to roundoff errors
                    new_viols = vtimes > old_time+100.0
                    if new_viols.any():
                        vtypes = tuple(np.char.lower(np.unique(vtypes[new_viols])))
                        vlimits = repr(vtypes).strip("('')")
                        if 'acis' in vlimits:
                            vlimits = vlimits.upper()
                        MSID = msid.upper()
                        email_txt = "<html>\n<head></head>\n<body>\n"
                        email_txt += "New violations of the {} {} limit(s) " \
                                     "have occurred.<br>\n\n".format(MSID, vlimits)
                        email_txt += "<font face='Menlo, monospace'>"
                        email_txt += "Type     Start                 Stop                  Max Temp Duration<br>\n"
                        email_txt += "-------- --------------------- --------------------- -------- --------<br>\n"
                        new_viol_idxs = np.where(new_viols)[0]
                        for idx in new_viol_idxs:
                            viol = viols[msid][idx]
                            if viol["type"].startswith("acis"):
                                vtype = viol["type"].upper()
                            else:
                                vtype = viol["type"].capitalize()
                            email_txt += "{:8} {:21} {:21} {:.2f} {:.2f}<br>\n".format(vtype,
                                                                                   viol["viol_datestart"],
                                                                                   viol["viol_datestop"],
                                                                                   viol["maxtemp"],
                                                                                   viol["duration"])
                        email_txt += "-------- --------------------- --------------------- -------- --------</font>\n\n"
                        url = "http://cxc.cfa.harvard.edu/acis/acis_viols_tracking/%s/viols_%s.html" % (self.now.year,
                                                                                                        msid)
                        email_txt += "<br><br>Visit %s for more details.\n" % url
                        email_txt += "</body>\n</html>"
                        msg = MIMEText(email_txt, 'html')
                        msg["To"] = "acisdude@head.cfa.harvard.edu"
                        msg["Subject"] = "New %s violations" % msid.upper()
                        p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
                        p.communicate(msg.as_bytes())
            # Now write the JSON file containing the latest
            # violations
            fp = open("last_viols.json", 'w')
            last_known_viols = {}
            for msid in temps:
                if len(viols[msid]) == 0:
                    last_known_viols[msid] = None
                else:
                    last_known_viols[msid] = viols[msid][-1]["viol_datestop"] 
            json.dump(last_known_viols, fp, indent=4)
            fp.close()

    def make_year_index(self):

        index_template = open(os.path.join('templates', 'year_template.rst')).read()
        index_template = re.sub(r' %}\n', ' %}', index_template)

        context = {"year": self.year}

        year_dir = os.path.join("source", str(self.year))
        if not os.path.exists(year_dir):
            os.mkdir(year_dir)
        outfile = os.path.join(year_dir, "index.rst")

        template = jinja2.Template(index_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))

    def make_index(self):
        index_template = open(os.path.join('templates', 'index_template.rst')).read()
        index_template = re.sub(r' %}\n', ' %}', index_template)

        years = [year.split("/")[-1] for year in glob.glob("source/20*")]
        years.sort(reverse=True)
        context = {"years": years,
                   "last_update": self.now.strftime("%Y:%j:%H:%M:%S")}

        outfile = os.path.join("source", "index.rst")

        template = jinja2.Template(index_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))


def make_and_run_tracker(end=None):
    plot_data = {}
    viols = {}
    viols_tracker = TrackACISViols(end=end)
    for msid in temps:
        viols[msid], plot_data[msid] = viols_tracker.find_viols(msid)
    viols_tracker.check_for_new_viols(viols)
    viols_tracker.make_year_index()
    viols_tracker.make_index()
    return plot_data


def make_combined_plots(plot_data):
    dstart = datetime(2016,1,1)
    dend = datetime.now()
    dt = dend-dstart
    nbins = dt.days//7
    bins = np.linspace(date2num(dstart), date2num(dend), nbins)
    for msid in temps:
        dates = defaultdict(list)
        diffs = defaultdict(list)
        durations = defaultdict(list)
        for year in plot_data.keys():
            lim_types = list(limits[msid][0].keys())
            lim_types.remove("start")
            year_doys = plot_data[year][msid][0]
            year_diffs = plot_data[year][msid][1]
            year_durations = plot_data[year][msid][2]
            for k in year_doys:
                if len(year_doys[k]) > 0:
                    cxctime = DateTime(["%s:%03d" % (year, doy) for doy in year_doys[k]]).secs
                    dates[k].extend(list(cxctime2plotdate(cxctime)))
                    diffs[k].extend(year_diffs[k])
                    durations[k].extend(year_durations[k])
        plt.rc("font", size=14)
        fig = plt.figure(figsize=(16, 5))
        ax = fig.add_subplot(131)
        for k in lim_types:
            ax.hist(dates[k], bins=bins, cumulative=True, histtype='step',
                    lw=3, label=k, color=colors[k])
        ax.xaxis_date()
        ax.set_xlabel("Date")
        ax.set_ylabel("# of violations")
        ax.legend(loc=2)
        ax.set_xlim(dstart, dend)
        years_fmt = DateFormatter('%Y-%j')
        ax.xaxis.set_major_formatter(years_fmt)
        ax2 = fig.add_subplot(132)
        ax2.xaxis_date()
        for k in lim_types:
            if len(dates[k]) > 0:
                ax2.scatter(num2date(dates[k]), diffs[k], marker='x', 
                            color=colors[k])
        ax2.set_xlabel("Date")
        ax2.set_ylabel(r"$\mathrm{\Delta{T}\ (^\circ{C})}$")
        ax2.xaxis.set_major_formatter(years_fmt)
        ax2.set_xlim(dstart, dend)
        _, ymax = ax2.get_ylim()
        ax2.set_ylim(0.0, max(1.5, ymax))
        ax3 = fig.add_subplot(133)
        ax3.xaxis_date()
        for k in lim_types:
            if len(dates[k]) > 0:
                ax3.scatter(num2date(dates[k]), durations[k], marker='x', 
                            color=colors[k])
        ax3.set_xlabel("Date")
        ax3.set_ylabel("Duration (ks)")
        ax3.set_xlim(dstart, dend)
        ax3.xaxis.set_major_formatter(years_fmt)
        _, ymax = ax3.get_ylim()
        ax3.set_ylim(0.0, max(10.0, ymax))
        fig.autofmt_xdate()
        fig.subplots_adjust(wspace=0.25)
        fig.savefig(os.path.join("source", "_static",
                                 "hist_%s.png" % msid))
        plt.close("all")


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Generate web pages which track ACIS violations.')
    parser.add_argument("start_year", type=int, 
                        help="The year to begin tracking the violations for.")
    parser.add_argument("--end_year", type=int, 
                        help="The year to end tracking the violations for. "
                             "Default: the current year.")
    args = parser.parse_args()
    plot_data = OrderedDict()
    if args.end_year is None:
        end_year = datetime.utcnow().year
    else:
        end_year = args.end_year
    years = range(args.start_year, end_year+1)
    for year in years:
        plot_data[year] = make_and_run_tracker(end=year)
    make_combined_plots(plot_data)
