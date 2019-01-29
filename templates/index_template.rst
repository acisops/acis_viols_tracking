.. acis_viols_tracking documentation master file, created by
   sphinx-quickstart on Sat Apr  7 11:10:18 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

{{msid}} Violations Tracking
===================================

High Violations
---------------

{% if hilo == "hi" %}

.. toctree::
   :maxdepth: 1

   {% for year in years %}{{year}}/viols_hi
   {% endfor %}long_term_hi

{% else %}

No high violations are currently reported for {{msid|upper}}.

{% endif %}

Low Violations
--------------

{% if hilo == "lo" %}

.. toctree::
   :maxdepth: 1

   {% for year in years %}{{year}}/viols_lo
   {% endfor %}long_term_lo

{% else %}

No low violations are currently reported for {{msid|upper}}.

{% endif %}


