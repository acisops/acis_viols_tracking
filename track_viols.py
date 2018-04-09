from __future__ import print_function
import acispy
from Chandra.cmd_states import fetch_states
from kadi import events
import numpy as np
from Chandra.Time import secs2date
import jinja2
import os
import re
from datetime import datetime
from calendar import monthrange

limits = {"1dpamzt": 35.5,
          "1deamzt": 35.5,
          "fptemp_11": {"ACIS-I": -114.0,
                        "ACIS-S": -112.0}
         }

class TrackACISViols(object):
    def __init__(self, end=None):
        if end is None:
            end = datetime.utcnow()
        else:
            end = datetime.strptime(end, "%Y:%j:%H:%M:%S")
        begin = datetime(end.year, 1, 1)
        datestart = begin.strftime("%Y:%j:%H:%M:%S")
        datestop = end.strftime("%Y:%j:%H:%M:%S")
        temps = ["fptemp_11", "1dpamzt", "1deamzt"]
        self.year = end.year
        self.ds = acispy.ArchiveData(datestart, datestop, temps, stat="5min")
        self.obsids = events.obsids.filter(start=datestart, stop=datestop)

    def find_viols(self, msid):
        if msid == "fptemp_11":
            viols = self._find_fptemp_viols(msid)
        else:
            viols = self._find_viols(msid)

        template_path = 'source/_templates'
        if msid == "fptemp_11":
            which = msid+"_"
        else:
            which = ""
        index_template_file = 'viols_%stemplate.rst' % which

        index_template = open(os.path.join(template_path, index_template_file)).read()
        index_template = re.sub(r' %}\n', ' %}', index_template)

        context = {"viols": viols}

        outfile = os.path.join("source", "viols_%s_%s.rst" % (msid, self.year))

        template = jinja2.Template(index_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))

    def _find_viols(self, msid):
        viols = []
        bad = np.concatenate(([False], self.ds[msid].value >= limits[msid], [False]))
        changes = np.flatnonzero(bad[1:] != bad[:-1]).reshape(-1, 2)
        for change in changes:
            viol = {'datestart': DateTime(times[change[0]]).date,
                    'datestop': DateTime(times[change[1] - 1]).date,
                    'maxtemp': temp[change[0]:change[1]].max()}
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
                tend_clock = self.ds["tstart"][when_clocking][-1].value
                temp_times = self.ds[msid].times.value
                idxs = np.logical_and(temp_times >= tbegin_clock, temp_times <= tend_clock)
                check_viol = (self.ds[msid][idxs].value > limits[msid][instr[0]]) & \
                            ~(self.ds[msid][idxs].value > -90.0)
                if np.any(check_viol):
                    duration = tend_clock-tbegin_clock
                    viol = {"obsid": obsid.obsid,
                            "tstart": tbegin_clock,
                            "tstop": tend_clock,
                            "datestart": secs2date(tbegin_clock),
                            "datestop": secs2date(tend_clock),
                            "instrument": instr[0],
                            "time_data": self.ds[msid].times[idxs].value,
                            "temp_data": self.ds[msid][idxs].value}
                    viols.append(viol)

        for i, viol in enumerate(viols):
            viol["maxtemp"] = viol["temp_data"].max()
            when = viol["temp_data"] > limits[msid][viol["instrument"]]
            viol["viol_tstart"], viol["viol_tstop"] = viol["time_data"][when][[0,-1]]
            viol["viol_datestart"] = secs2date(viol["viol_tstart"])
            viol["viol_datestop"] = secs2date(viol["viol_tstop"])
            viol["duration"] = viol["viol_tstop"]-viol["viol_tstart"]
            dp = acispy.DatePlot(self.ds, msid, figsize=(11, 8))
            otime = viol["tstop"]-viol["tstart"]
            plot_tbegin = viol["tstart"]-0.5*otime
            plot_tend = viol["tstop"]+0.5*otime
            dp.set_xlim(secs2date(plot_tbegin), secs2date(plot_tend))
            dp.add_vline(secs2date(viol['tstart']), color='orange')
            dp.add_vline(secs2date(viol['tstop']), color='orange')
            dp.add_hline(limits[msid][viol['instrument']], ls='--')
            dp.set_ylabel(r"$\mathrm{Temperature\ (^\circ{C})}$")
            plot_idxs = np.logical_and(dp.times["msids","fptemp_11"].value >= plot_tbegin,
                                       dp.times["msids","fptemp_11"].value <= plot_tend)
            ymax = dp.y["msids","fptemp_11"][plot_idxs].value.max()+1.0
            ymin = dp.y["msids","fptemp_11"][plot_idxs].value.min()-1.0
            dp.set_ylim(ymin, ymax)
            fn = "fptemp_%s_%d.png" % (self.year, i)
            dp.savefig(os.path.join("source/_static", fn))
            viol["plot"] = os.path.join("_static", fn)

        return viols
        
viols_tracker = TrackACISViols()
viols_tracker.find_viols("fptemp_11")