import matplotlib as mpl
mpl.use('Agg')
mpl.rcParams.update({'figure.max_open_warning': 0})
import matplotlib.pyplot as plt
plt.ioff()
import acispy
from kadi import events
import numpy as np
from cxotime import CxoTime
import jinja2
import os
import re
from datetime import datetime
import glob
from collections import defaultdict
from Ska.Matplotlib import cxctime2plotdate
from matplotlib.dates import num2date, DateFormatter, date2num
from email.mime.text import MIMEText
import json
from acispy.utils import mylog
from acis_thermal_check import fetch_ocat_data
from IPython import embed
import smtplib
import warnings
mylog.setLevel(40)

secs2date = lambda x: CxoTime(x).date
date2secs = lambda x: CxoTime(x).secs

colors = {"Planning_hi": "green",
          "Yellow_hi": "gold",
          "Planning_lo": "green",
          "Yellow_lo": "gold",
          "ACIS-I": "C0",
          "ACIS-S": "C1",
          "ACIS-H": "red",
          "zero_feps": "dodgerblue"}

labels = {"Planning_hi": "Planning High",
          "Planning_lo": "Planning Low",
          "Yellow_hi": "Yellow High",
          "Yellow_lo": "Yellow Low",
          "zero_feps": "Zero FEPs",
          "ACIS-I": "ACIS-I",
          "ACIS-S": "ACIS-S",
          "ACIS-H": "ACIS-H"}

with open("limits.json", "r") as f:
    limits = json.load(f)
temps = list(limits.keys())

warnings.filterwarnings("ignore", "erfa")

class TrackACISViols:
    def __init__(self, end=None, to_addr=None):
        if to_addr is None:
            to_addr = "acisdude@cfa.harvard.edu"
        self.to_addr = to_addr
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
        self.ds = acispy.TelemData(datestart, datestop, temps, 
                                   stat="5min", recent_source='tracelog')
        obsids = events.obsids.filter(start=datestart, stop=datestop)
        self.obsids = [o for o in obsids if o.obsid > 0 and o.obsid < 38000]
        self.obsids.sort(key=lambda o: o.obsid)
        self.ds.map_state_to_msid("fep_count", "1dpamzt")
    
    def find_viols(self, msid, hilo):
        lim_types = list(limits[msid][0])
        lim_types.remove("start")

        if msid == "fptemp_11":
            viols, num_viols = self._find_fptemp_viols(msid)
        elif msid == "1dpamzt":
            viols, num_viols = self._find_dpa_viols(msid)
        else:
            viols, num_viols = self._find_viols(msid, hilo)
        plot_data = self._make_plots(msid, viols, hilo)

        if msid in ["fptemp_11", "1dpamzt"]:
            which = msid+"_"
        else:
            which = hilo+"_"
        viols_template_file = 'viols_%stemplate.rst' % which

        viols_template = open(os.path.join('templates', viols_template_file)).read()
        viols_template = re.sub(r' %}\n', ' %}', viols_template)

        plan = any([lt.startswith("Planning") for lt in lim_types])

        context = {"plan": plan,
                   "viols": viols,
                   "num_viols": num_viols,
                   "year": self.year,
                   "msid": msid.upper(),
                   "last_update": datetime.utcnow().strftime("%Y:%j:%H:%M:%S")}

        year_dir = os.path.join("source", msid.lower(), str(self.year))
        if not os.path.exists(year_dir):
            os.makedirs(year_dir)
        if msid in ["fptemp_11", "1dpamzt"]:
            outfile = "viols.rst"
        else:
            outfile = "viols_%s.rst" % hilo
        outfile = os.path.join(year_dir, outfile)

        template = jinja2.Template(viols_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))

        return viols, plot_data

    def _find_viols(self, msid, hilo):
        lim_types = list(limits[msid][0])
        lim_types.remove("start")
        num_viols = defaultdict(int)
        viols = []
        msid_times = self.ds[msid].times.value
        msid_vals = self.ds[msid].value
        for ltype in lim_types:
            if ltype.startswith("ACIS") or ltype.startswith("zero"):
                continue
            limit_vals = np.zeros(msid_vals.size)
            for lim in limits[msid]:
                lim_start = date2secs(lim["start"])
                limit_vals[msid_times >= lim_start] = lim[ltype]
            if ltype.endswith("lo"):
                op = np.less_equal
                reduce = np.min
                redkey = "mintemp"
            elif ltype.endswith("hi"):
                op = np.greater_equal
                reduce = np.max
                redkey = "maxtemp"
            else:
                raise RuntimeError("Invalid limit type!")
            with np.errstate(invalid='ignore'):
                bad = np.concatenate(([False], op(msid_vals, limit_vals), [False]))
            changes = np.flatnonzero(bad[1:] != bad[:-1]).reshape(-1, 2)
            for change in changes:
                duration = msid_times[change[1] - 1] - msid_times[change[0]]
                if duration < 10.0:
                    continue
                viol = {'viol_tstart': msid_times[change[0]],
                        'viol_tstop': msid_times[change[1] - 1],
                        redkey: float(reduce(msid_vals[change[0]:change[1]])),
                        'limit': limit_vals[change[0]],
                        'type': ltype}
                viol["viol_datestart"] = secs2date(viol["viol_tstart"])
                viol["viol_datestop"] = secs2date(viol["viol_tstop"])
                viol["duration"] = (viol["viol_tstop"]-viol["viol_tstart"])/1000.0
                viols.append(viol)
                num_viols[ltype] += 1
        return viols, num_viols

    def _find_dpa_viols(self, msid):
        viols = []
        num_viols = {"zero_feps": 0}
        when_zero = self.ds["msids","fep_count"] == 0
        msid_times = self.ds[msid].times.value
        msid_vals = self.ds[msid].value
        time_data = msid_times[when_zero]
        msid_data = msid_vals[when_zero]
        limit_vals = np.zeros(msid_data.size)
        for lim in limits[msid]:
            lim_start = date2secs(lim["start"])
            limit_vals[time_data >= lim_start] = lim["zero_feps"]        
        bad = np.less_equal(msid_data, limit_vals)
        with np.errstate(invalid='ignore'):
            bad = np.concatenate(([False], bad, [False]))
        if np.any(bad):
            changes = np.flatnonzero(bad[1:] != bad[:-1]).reshape(-1, 2)
            for change in changes:
                duration = time_data[change[1] - 1] - time_data[change[0]]
                if duration < 10.0:
                    continue
                viol = {'limit': limit_vals[change[0]],
                        'type': 'zero_feps',
                        "time_data": msid_times[when_zero].tolist(),
                        "temp_data": msid_vals[when_zero].tolist()}
                viol['viol_tstart'] = viol["time_data"][change[0]]
                viol['viol_tstop'] = viol["time_data"][change[1] - 1]
                viol['mintemp'] = float(np.max(viol["temp_data"][change[0]:change[1]]))
                viol["viol_datestart"] = secs2date(viol["viol_tstart"])
                viol["viol_datestop"] = secs2date(viol["viol_tstop"])
                viol["duration"] = (viol["viol_tstop"]-viol["viol_tstart"])/1000.0
                viols.append(viol)
                num_viols["zero_feps"] += 1
        viols_hi, num_viols_hi = self._find_viols("1dpamzt", "hi")
        viols += viols_hi
        num_viols["Planning_hi"] = num_viols_hi["Planning_hi"]
        num_viols["Yellow_hi"] = num_viols_hi["Yellow_hi"]
        return viols, num_viols

    def _find_fptemp_viols(self, msid):
        num_viols = {
            "ACIS_I": 0, 
            "ACIS_S": 0,
            "ACIS_H": 0
        }
        viols = []
        msid_times = self.ds[msid].times.value
        msid_vals = self.ds[msid].value
        obsids = [o.obsid for o in self.obsids]
        hot_acis = np.empty(0, dtype='bool')
        oo = np.empty(0, dtype='int')
        for o in np.array_split(obsids, 20): 
            ocat_data = fetch_ocat_data(o)
            hetg = ocat_data["grating"] == "HETG"
            s3_only = (ocat_data["S3"] == "Y") & (ocat_data["ccd_count"] == 1)
            oo = np.append(oo, ocat_data["obsid"])
            hot_acis = np.append(hot_acis, 
                                 hetg | ((ocat_data["num_counts"] < 300.0) & s3_only))
        hot_acis = hot_acis[np.argsort(oo)]
        for i, obsid in enumerate(self.obsids):
            when_clocking = ((self.ds["clocking"] == 1) &
                             (self.ds["tstart"].value >= obsid.tstart) &
                             (self.ds["tstop"].value <= obsid.tstop))
            instr = self.ds["instrument"][when_clocking]
            if len(instr.value) < 1 or np.char.startswith(instr.value, "HRC").any():
                continue
            if not np.all(instr == instr[0]):
                print(instr)
                raise RuntimeError("OOPS!")
            this_instr = instr[0]
            if this_instr == "ACIS-S" and hot_acis[i]:
                this_instr = "ACIS-H"
            tbegin_clock = self.ds["tstart"][when_clocking][0].value
            tend_clock = self.ds["tstop"][when_clocking][-1].value
            idxs = np.logical_and(msid_times >= tbegin_clock, msid_times <= tend_clock)
            this_limit = None
            for lim in limits[msid]:
                lim_start = date2secs(lim["start"])
                if tbegin_clock >= lim_start:
                    this_limit = lim[this_instr]
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
                            "type": this_instr,
                            "time_data": msid_times[idxs].tolist(),
                            "temp_data": msid_vals[idxs].tolist()}
                    viol["maxtemp"] = float(np.max(viol["temp_data"][change[0]:change[1]]))
                    viol['viol_tstart'] = viol["time_data"][change[0]]
                    viol['viol_tstop'] = viol["time_data"][change[1] - 1]
                    viol["viol_datestart"] = secs2date(viol["viol_tstart"])
                    viol["viol_datestop"] = secs2date(viol["viol_tstop"])
                    viol["duration"] = (viol["viol_tstop"]-viol["viol_tstart"])/1000.0
                    viols.append(viol)
                    num_viols[instr[0].replace("-","_")] += 1
        viols_hi, num_viols_hi = self._find_viols("fptemp_11", "hi")
        viols += viols_hi
        num_viols["Planning_hi"] = num_viols_hi["Planning_hi"]
        num_viols["Yellow_hi"] = num_viols_hi["Yellow_hi"]
        return viols, num_viols

    def _make_plots(self, msid, viols, hilo):
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
            if msid == "1dpamzt" and viol["type"] == "zero_feps":
                field2 = ("states", "fep_count")
            else:
                field2 = ("states", "pitch")
            dp = acispy.DatePlot(self.ds, msid, figsize=(11, 8), field2=field2)
            doys[viol["type"]].append(doy)
            if viol["type"] == "zero_feps":
                redkey = "mintemp"
            elif msid == "fptemp_11":
                redkey = "maxtemp"
            else:
                redkey = "mintemp" if hilo == "lo" else "maxtemp"
            diffs[viol["type"]].append(np.abs(viol[redkey]-viol["limit"]))
            durations[viol["type"]].append(viol["duration"])
            if msid == "fptemp_11" and not viol["type"].endswith("hi"):
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
                dp.add_hline(viol['limit'], ls='-')
            elif msid == "1dpamzt" and viol["type"] == "zero_feps":
                for lim in limits[msid]:
                    lim_start = date2secs(lim["start"])
                    if viol["viol_tstart"] >= lim_start:
                        zlimit = lim["zero_feps"]
                dp.add_hline(zlimit, ls='--', color=colors["zero_feps"])
                otime = viol["viol_tstop"]-viol["viol_tstart"]
                plot_tbegin = viol["viol_tstart"]-otime
                plot_tend = viol["viol_tstop"]+otime
            else:
                plimit = None
                ylimit = None
                for lim in limits[msid]:
                    lim_start = date2secs(lim["start"])
                    if viol["viol_tstart"] >= lim_start:
                        plimit = lim.get("Planning_%s" % hilo, None)
                        ylimit = lim.get("Yellow_%s" % hilo, None)
                if plimit is not None:
                    dp.add_hline(plimit, ls='-', color=colors["Planning_%s" % hilo])
                if ylimit is not None:
                    dp.add_hline(ylimit, ls='-', color=colors["Yellow_%s" % hilo])
                otime = viol["viol_tstop"]-viol["viol_tstart"]
                plot_tbegin = viol["viol_tstart"]-otime
                plot_tend = viol["viol_tstop"]+otime
            ymin, ymax = dp.ax.get_ylim()
            dp.set_xlim(secs2date(plot_tbegin), secs2date(plot_tend))
            dp.set_ylabel(r"$\mathrm{Temperature\ (^\circ{C})}$")
            title = "Violation start: {}\n" \
                    "Violation stop: {}\n" \
                    "Violation duration: {:.2f} ks".format(viol["viol_datestart"],
                                                           viol["viol_datestop"],
                                                           viol["duration"])
            if msid == "fptemp_11" and not viol["type"].endswith("hi"):
                title += ", OBSID: {}".format(viol["obsid"])
            dp.set_title(title)
            plot_idxs = np.logical_and(dp.times["msids", msid].value >= plot_tbegin,
                                       dp.times["msids", msid].value <= plot_tend)
            ymax = np.nanmax(dp.y["msids", msid][plot_idxs].value)+1.0
            ymin = np.nanmin(dp.y["msids", msid][plot_idxs].value)-1.0
            dp.set_ylim(ymin, ymax)
            tplot = cxctime2plotdate(dp.y["msids", msid].times.value)
            viol_idxs = np.logical_and(dp.times["msids", msid].value >= viol["viol_tstart"],
                                       dp.times["msids", msid].value <= viol["viol_tstop"])
            dp.ax.fill_between(tplot, ymin, ymax, where=viol_idxs, color="C3", alpha=0.5)
            if msid == "fptemp_11":
                fn = "%s_%s_%d.png" % (msid, self.year, i)
            elif msid == "1dpamzt" and viol["type"] == "zero_feps":
                fn = "%s_%s_zero_%d.png" % (msid, self.year, i)
            else:
                fn = "%s_%s_%s_%d.png" % (msid, self.year, hilo, i)
            if not os.path.exists("source/_static"):
                os.mkdir("source/_static")
            dp.savefig(os.path.join("source/_static", fn))
            viol["plot"] = os.path.join("../..", "_static", fn)
        plt.rc("font", size=14)
        fig = plt.figure(figsize=(16, 5))
        ax = fig.add_subplot(131)
        if self.year == self.now.year:
            max_doys = self.now.timetuple().tm_yday
        else:
            max_doys = 365
            if int(self.year) % 4 == 0:
                max_doys += 1
        if max_doys <= 21:
            nbins = max_doys
        else:
            nbins = max_doys // 7
        bins = np.linspace(1, max_doys, nbins)
        for key in lim_types:
            ax.hist(doys[key], bins=bins, cumulative=True, histtype='step',
                    lw=3, label=labels[key], color=colors[key])
        ax.set_xlim(1, max_doys)
        ax.set_xlabel("DOY")
        ax.set_ylabel("# of violations")
        ax.legend(loc=2)
        ax2 = fig.add_subplot(132)
        for key in doys:
            if len(doys[key]) > 0:
                ax2.scatter(doys[key], diffs[key], marker='x',
                            color=colors[key])
        ax2.set_xlim(1, max_doys)
        ax2.set_xlabel("DOY")
        ax2.set_ylabel(r"$\mathrm{\Delta{T}\ (^\circ{C})}$")
        _, ymax = ax2.get_ylim()
        ax2.set_ylim(0.0, max(1.5, ymax))
        ax3 = fig.add_subplot(133)
        for key in doys:
            if len(doys[key]) > 0:
                ax3.scatter(doys[key], durations[key], marker='x',
                            color=colors[key])
        ax3.set_xlim(1, max_doys)
        ax3.set_xlabel("DOY")
        ax3.set_ylabel("Duration (ks)")
        _, ymax = ax3.get_ylim()
        ax3.set_ylim(0.0, max(10.0, ymax))
        fig.subplots_adjust(wspace=0.25)
        if msid in ["fptemp_11", "1dpamzt"]:
            outfile = "hist_%s_%s.png" % (msid, self.year)
        else:
            outfile = "hist_%s_%s_%s.png" % (msid, self.year, hilo)
        fig.savefig(os.path.join("source", "_static", outfile))
        plt.close("all")
        return doys, diffs, durations

    def check_for_new_viols(self, msid, hilo, viols):
        from email.message import EmailMessage
        msg = None
        # Check to see if there are any new violations
        # since the last time we looked
        if self.year == self.now.year:
            if os.path.exists("last_viols.json"):
                with open("last_viols.json", "r") as f:
                    last_known_viols = json.load(f)
            else:
                last_known_viols = {}
            if len(viols[msid]) == 0: 
                vtimes = None
            else:
                vtimes = np.array([viol["viol_tstop"] for viol in viols[msid] 
                                   if viol["type"] != "zero_feps"])
                vtypes = np.array([viol["type"] for viol in viols[msid]
                                   if viol["type"] != "zero_feps"])
                if last_known_viols.get(msid, None) is None:
                    new_viols = np.ones_like(vtimes, dtype='bool')
                else:
                    old_time = date2secs(last_known_viols[msid])
                    # Buffer this by ~100 s to avoid spurious
                    # reports due to roundoff errors
                    new_viols = vtimes > old_time+100.0
                if new_viols.any():
                    vtypes = tuple(np.char.lower(np.unique(vtypes[new_viols])))
                    vlimits = repr(vtypes).strip("('')").strip("'")
                    if 'acis' in vlimits:
                        vlimits = vlimits.upper()
                    MSID = msid.upper()
                    email_txt = "<html>\n<head></head>\n<body>\n"
                    email_txt += f"New limit violations for {MSID} have occurred.<br><br><br>\n"
                    email_txt += "<font face='Menlo, monospace'>"
                    email_txt += "<pre class=\"tab\">Type     Start                 Stop                  Viol Temp Duration</pre><br>\n"
                    email_txt += "-------- --------------------- --------------------- --------- --------<br>\n"
                    new_viol_idxs = np.where(new_viols)[0]
                    for idx in new_viol_idxs:
                        viol = viols[msid][idx]
                        vtype = labels[viol["type"]]
                        if 'maxtemp' in viol:
                            reduce = 'max'
                        elif 'mintemp' in viol:
                            reduce = 'min'
                        email_txt += "{:8} {:21} {:21} {:.2f} {:.2f}<br>\n".format(vtype,
                                                                                   viol["viol_datestart"],
                                                                                   viol["viol_datestop"],
                                                                                   viol["%stemp" % reduce],
                                                                                   viol["duration"])
                    email_txt += "-------- --------------------- --------------------- -------- --------</font>\n\n"
                    if msid in ["fptemp_11", "1dpamzt"]:
                        page = "viols.html"
                    else:
                        page = "viols_%s.html" % hilo
                    url = "http://cxc.cfa.harvard.edu/acis/acis_viols_tracking/%s/%s/%s" % (msid, self.now.year,
                                                                                            page)
                    email_txt += "<br><br>Visit %s for more details.\n" % url
                    email_txt += "</body>\n</html>"
                    msg = EmailMessage()
                    msg.set_content(email_txt, 'html')
                    msg["To"] = self.to_addr
                    msg["From"] = "acisdude@cfa.harvard.edu"
                    msg["Subject"] = "New %s violations" % msid.upper()
            # Now write the JSON file containing the latest
            # violations
            with open("last_viols.json", 'w') as fp:
                if vtimes is None or len(vtimes) == 0:
                    last_known_viols[msid] = None
                else:
                    last_known_viols[msid] = secs2date(vtimes.max())
                json.dump(last_known_viols, fp, indent=4)

        return msg

    def make_index(self, msid, hilo):
        if msid in ["fptemp_11", "1dpamzt"]:
            index_template = f"index_{msid}_template.rst"
        else:
            index_template = 'index_template.rst'
        index_template = open(os.path.join('templates', index_template)).read()
        index_template = re.sub(r' %}\n', ' %}', index_template)

        years = [year.split("/")[-1] for year in glob.glob("source/{}/20*".format(msid.lower()))]
        years.sort(reverse=True)
        context = {"msid": msid.upper(),
                   "years": years,
                   "hilo": hilo}

        outfile = os.path.join("source", msid.lower(), "index.rst")

        template = jinja2.Template(index_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))


def make_and_run_tracker(year, end_year, to_addr):
    if not os.path.exists("source/_static"):
        os.mkdir("source/_static")
    plot_data = {}
    viols = {}
    viols_tracker = TrackACISViols(end=year, to_addr=to_addr)
    msgs = []
    for msid in temps:
        plot_data_json = os.path.join("source/_static",
                                      "{}_{}_plot_data.json".format(msid, year))
        if year != end_year and os.path.exists(plot_data_json):
            with open(plot_data_json, "r") as f:
                plot_data[msid] = json.load(f)
        else:
            if msid == "fptemp_11":
                hilo = "hi"
            else:
                lim_types = list(limits[msid][0])
                lim_types.remove("start")
                hilo = lim_types[0][-2:]
            viols[msid], plot_data[msid] = viols_tracker.find_viols(msid, hilo)
            if year != end_year:
                with open(plot_data_json, "w") as f:
                    json.dump(plot_data[msid], f, sort_keys=True, indent=4)
            msg = viols_tracker.check_for_new_viols(msid, hilo, viols)
            viols_tracker.make_index(msid, hilo)
            if msg is not None:
                msgs.append(msg)
    return plot_data, msgs


def make_combined_plots(plot_data):
    dstart = datetime(2016,1,1)
    dend = datetime.now()
    dt = dend-dstart
    nbins = dt.days//7
    bins = np.linspace(date2num(dstart), date2num(dend), nbins)
    for msid in temps:
        if msid == "fptemp_11":
            hilo = "hi"
        else:
            lim_types = list(limits[msid][0])
            lim_types.remove("start")
            hilo = lim_types[0][-2:]
        dates = defaultdict(list)
        diffs = defaultdict(list)
        durations = defaultdict(list)
        lim_types = list(limits[msid][0].keys())
        lim_types.remove("start")
        for year in plot_data.keys():
            year_doys = plot_data[year][msid][0]
            year_diffs = plot_data[year][msid][1]
            year_durations = plot_data[year][msid][2]
            for k in year_doys:
                if len(year_doys[k]) > 0:
                    cxctime = CxoTime(["%s:%03d" % (year, doy) for doy in year_doys[k]]).secs
                    dates[k].extend(list(cxctime2plotdate(cxctime)))
                    diffs[k].extend(year_diffs[k])
                    durations[k].extend(year_durations[k])
        plt.rc("font", size=14)
        fig = plt.figure(figsize=(16, 5))
        ax = fig.add_subplot(131)
        for key in lim_types:
            ax.hist(dates[key], bins=bins, cumulative=True, histtype='step',
                    lw=3, label=labels[key], color=colors[key])
        ax.xaxis_date()
        ax.set_xlabel("Date")
        ax.set_ylabel("# of violations")
        ax.legend(loc=2)
        ax.set_xlim(dstart, dend)
        _, ymax = ax.get_ylim()
        ax.set_ylim(0.0, max(1.1, ymax))
        years_fmt = DateFormatter('%Y-%j')
        ax.xaxis.set_major_formatter(years_fmt)
        ax2 = fig.add_subplot(132)
        ax2.xaxis_date()
        for key in lim_types:
            if len(dates[key]) > 0:
                ax2.scatter(num2date(dates[key]), diffs[key], marker='x',
                            color=colors[key])
        ax2.set_xlabel("Date")
        ax2.set_ylabel(r"$\mathrm{\Delta{T}\ (^\circ{C})}$")
        ax2.xaxis.set_major_formatter(years_fmt)
        ax2.set_xlim(dstart, dend)
        _, ymax = ax2.get_ylim()
        ax2.set_ylim(0.0, max(1.5, ymax))
        ax3 = fig.add_subplot(133)
        ax3.xaxis_date()
        for key in lim_types:
            if len(dates[key]) > 0:
                ax3.scatter(num2date(dates[key]), durations[key], marker='x',
                            color=colors[key])
        ax3.set_xlabel("Date")
        ax3.set_ylabel("Duration (ks)")
        ax3.set_xlim(dstart, dend)
        ax3.xaxis.set_major_formatter(years_fmt)
        _, ymax = ax3.get_ylim()
        ax3.set_ylim(0.0, max(10.0, ymax))
        fig.autofmt_xdate()
        fig.subplots_adjust(wspace=0.25)
        if msid in ["fptemp_11", "1dpamzt"]:
            outfile = "hist_%s.png" % msid
        else:
            outfile = "hist_%s_%s.png" % (msid, hilo)
        fig.savefig(os.path.join("source", "_static", outfile))
        plt.close("all")


def make_long_term():

    index_template = open(os.path.join('templates', 'long_term_template.rst')).read()
    index_template = re.sub(r' %}\n', ' %}', index_template)

    for msid in temps:
        context = {"msid": msid.lower(),
                   "last_update": datetime.utcnow().strftime("%Y:%j:%H:%M:%S")}
        if msid in ["fptemp_11", "1dpamzt"]:
            context["title"] = f"Long-Term {msid.upper()} Violation Trends"
            context["histfile"] = f"hist_{msid.lower()}.png"
            outfile = "long_term.rst"
        else:
            lim_types = list(limits[msid][0])
            lim_types.remove("start")
            hilo = lim_types[0][-2:]
            context["title"] = "Long-Term %s %s Violation Trends" % (msid.upper(),
                                                                     {"hi": "High", "lo": "Low"}[hilo])
            context["histfile"] = "hist_%s_%s.png" % (msid, hilo)
            outfile = "long_term_%s.rst" % hilo
        msid_dir = os.path.join("source", msid.lower())
        if not os.path.exists(msid_dir):
            os.makedirs(msid_dir)
        outfile = os.path.join(msid_dir, outfile)

        template = jinja2.Template(index_template)

        with open(outfile, "w") as f:
            f.write(template.render(**context))


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Generate web pages which track ACIS violations.')
    parser.add_argument("start_year", type=int, 
                        help="The year to begin tracking the violations for.")
    parser.add_argument("--end_year", type=int, 
                        help="The year to end tracking the violations for. "
                             "Default: the current year.")
    parser.add_argument("--to_addr", type=str,
                        help="The email to send violation information to. Default: "
                             "acisdude@cfa.harvard.edu")
    args = parser.parse_args()
    plot_data = {}
    if args.end_year is None:
        end_year = datetime.utcnow().year
    else:
        end_year = args.end_year
    years = range(args.start_year, end_year+1)
    msgs = []
    for year in years:
        plot_data[year], new_msgs = make_and_run_tracker(year, end_year, args.to_addr)
        msgs += new_msgs
    make_combined_plots(plot_data)
    make_long_term()
    with smtplib.SMTP('localhost') as s:
        for msg in msgs:
            s.send_message(msg)

