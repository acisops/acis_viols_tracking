from __future__ import print_function
import acispy
from kadi import events
import numpy as np
from Chandra.Time import secs2date
import jinja2
import os
import re
from datetime import datetime
import glob
import matplotlib.pyplot as plt
from collections import defaultdict

limits = {"1dpamzt": {"Planning": 35.5,
                      "Yellow": 37.5},
          "1deamzt": {"Planning": 35.5,
                      "Yellow": 37.5},
          "1pdeaat": {"Planning": 52.5,
                      "Yellow": 57.0},
          "fptemp_11": {"ACIS-I": -114.0,
                        "ACIS-S": -112.0}
         }

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
        temps = list(limits.keys())
        self.year = end.year
        print("Tracking violations for the year %s." % self.year)
        self.now = now
        self.ds = acispy.ArchiveData(datestart, datestop, temps, stat="5min")
        self.obsids = events.obsids.filter(start=datestart, stop=datestop)

    def find_viols(self, msid):
        if msid == "fptemp_11":
            viols = self._find_fptemp_viols(msid)
        else:
            viols = self._find_viols(msid)
        if len(viols) > 0:
            self._make_plots(msid, viols)

        if msid == "fptemp_11":
            which = msid+"_"
        else:
            which = ""
        viols_template_file = 'viols_%stemplate.rst' % which

        viols_template = open(os.path.join('templates', viols_template_file)).read()
        viols_template = re.sub(r' %}\n', ' %}', viols_template)

        context = {"viols": viols,
                   "year": self.year,
                   "msid": msid.upper()}

        year_dir = os.path.join("source", str(self.year))
        if not os.path.exists(year_dir):
            os.mkdir(year_dir)
        outfile = os.path.join(year_dir, "viols_%s.rst" % msid)

        template = jinja2.Template(viols_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))

    def _find_viols(self, msid):
        viols = []
        for ltype in ["Planning", "Yellow"]:
            bad = np.concatenate(([False], self.ds[msid].value >= limits[msid][ltype], [False]))
            changes = np.flatnonzero(bad[1:] != bad[:-1]).reshape(-1, 2)
            for change in changes:
                viol = {'viol_tstart': self.ds[msid].times.value[change[0]],
                        'viol_tstop': self.ds[msid].times.value[change[1] - 1],
                        'maxtemp': self.ds[msid].value[change[0]:change[1]].max(),
                        'limit': limits[msid][ltype],
                        'type': ltype}
                viol["viol_datestart"] = secs2date(viol["viol_tstart"])
                viol["viol_datestop"] = secs2date(viol["viol_tstop"])
                viol["duration"] = (viol["viol_tstop"]-viol["viol_tstart"])/1000.0
                viols.append(viol)
        return viols

    def _find_fptemp_viols(self, msid):
        viols = []
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
                temp_times = self.ds[msid].times.value
                idxs = np.logical_and(temp_times >= tbegin_clock, temp_times <= tend_clock)
                bad = (self.ds[msid][idxs].value > limits[msid][instr[0]]) & \
                     ~(self.ds[msid][idxs].value > -90.0)
                bad = np.concatenate(([False], bad, [False]))
                if np.any(bad):
                    changes = np.flatnonzero(bad[1:] != bad[:-1]).reshape(-1, 2)
                    for change in changes:
                        time_data = self.ds[msid].times[idxs].value
                        duration = time_data[change[1] - 1] - time_data[change[0]]
                        if duration < 10.0:
                            continue
                        viol = {"obsid": obsid.obsid,
                                "limit": limits[msid][instr[0]],
                                "tstart": tbegin_clock,
                                "tstop": tend_clock,
                                "datestart": secs2date(tbegin_clock),
                                "datestop": secs2date(tend_clock),
                                "type": instr[0],
                                "time_data": self.ds[msid].times[idxs].value,
                                "temp_data": self.ds[msid][idxs].value}
                        viol["maxtemp"] = viol["temp_data"][change[0]:change[1]].max()
                        viol['viol_tstart'] = viol["time_data"][change[0]]
                        viol['viol_tstop'] = viol["time_data"][change[1] - 1]
                        viol["viol_datestart"] = secs2date(viol["viol_tstart"])
                        viol["viol_datestop"] = secs2date(viol["viol_tstop"])
                        viol["duration"] = (viol["viol_tstop"]-viol["viol_tstart"])/1000.0
                        viols.append(viol)
        return viols

    def _make_plots(self, msid, viols):
        doys = defaultdict(list)
        diffs = defaultdict(list)
        for i, viol in enumerate(viols):
            doy = datetime.strptime(viol["viol_datestop"].split(".")[0],
                                    "%Y:%j:%H:%M:%S").timetuple().tm_yday
            dp = acispy.DatePlot(self.ds, msid, figsize=(11, 8))
            doys[viol["type"]].append(doy)
            diffs[viol["type"]].append(viol["maxtemp"]-viol["limit"])
            if msid == "fptemp_11":
                otime = viol["tstop"]-viol["tstart"]
                plot_tbegin = viol["tstart"]-0.5*otime
                plot_tend = viol["tstop"]+0.5*otime
                dp.add_vline(secs2date(viol['tstart']), color='orange')
                dp.add_vline(secs2date(viol['tstop']), color='orange')
            else:
                otime = viol["viol_tstop"]-viol["viol_tstart"]
                plot_tbegin = viol["viol_tstart"]-otime
                plot_tend = viol["viol_tstop"]+otime
            dp.add_hline(viol['limit'], ls='--')
            dp.set_xlim(secs2date(plot_tbegin), secs2date(plot_tend))
            dp.set_ylabel(r"$\mathrm{Temperature\ (^\circ{C})}$")
            plot_idxs = np.logical_and(dp.times["msids", msid].value >= plot_tbegin,
                                       dp.times["msids", msid].value <= plot_tend)
            ymax = dp.y["msids", msid][plot_idxs].value.max()+1.0
            ymin = dp.y["msids", msid][plot_idxs].value.min()-1.0
            dp.set_ylim(ymin, ymax)
            fn = "%s_%s_%d.png" % (msid, self.year, i)
            dp.savefig(os.path.join("source/_static", fn))
            viol["plot"] = os.path.join("..", "_static", fn)
        plt.rc("font", size=14)
        fig = plt.figure(figsize=(12, 5))
        ax = fig.add_subplot(121)
        if self.year == self.now.year:
            max_doys = self.now.timetuple().tm_yday
        else:
            max_doys = 365
            if int(self.year) % 4 == 0:
                max_doys += 1
        bins = np.linspace(1, max_doys, max_doys // 7)
        for k in doys:
            ax.hist(doys[k], bins=bins, cumulative=True, histtype='step',
                    lw=3, label=k)
        ax.set_xlim(1, max_doys)
        ax.set_xlabel("DOY")
        ax.set_ylabel("# of violations")
        ax.legend(loc=2)
        ax2 = fig.add_subplot(122)
        for k in doys:
            ax2.scatter(doys[k], diffs[k], marker='x')
        ax2.set_xlim(1, max_doys)
        ax2.set_xlabel("DOY")
        ax2.set_ylabel(r"$\mathrm{\Delta{T}\ (^\circ{C})}$")
        fig.subplots_adjust(wspace=0.25)
        fig.savefig(os.path.join("source", "_static",
                                 "hist_%s_%s.png" % (msid, self.year)))
        plt.close(fig)

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
        context = {"years": years}

        outfile = os.path.join("source", "index.rst")

        template = jinja2.Template(index_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))

def make_and_run_tracker(end=None):
    viols_tracker = TrackACISViols(end=end)
    for msid in limits.keys():
        viols_tracker.find_viols(msid)
    viols_tracker.make_year_index()
    viols_tracker.make_index()

if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Generate web pages which track ACIS violations.')
    parser.add_argument("--years", help="A comma-separated list of years to generate "
                                        "pages for.")
    args = parser.parse_args()
    if args.years is None:
        make_and_run_tracker()
    else:
        years = [int(year) for year in args.years.split(",")]
        for year in years:
            make_and_run_tracker(end=year)
