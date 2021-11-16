{{year}} Focal Plane Temperature Violations
-------------------------------------------

ACIS-I Violations
=================

{% if num_viols.ACIS_I == 0 %}
No ACIS-I limit violations during this period. 
{% else %}
=====================  =====================  ==================  =============  =======  ===================
Date start             Date stop              Max temperature     Duration (ks)  Obsid    Plot
=====================  =====================  ==================  =============  =======  ===================
{% for viol in viols %}
{% if viol.type == "ACIS-I" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}             {{"%2.2f"|format(viol.duration)}}           {{viol.obsid}}        `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  =======  ===================
{% endif %}

ACIS-S Violations
=================

{% if num_viols.ACIS_S == 0 %}
No ACIS-S limit violations during this period. 
{% else %}
=====================  =====================  ==================  =============  =======  ===================
Date start             Date stop              Max temperature     Duration (ks)  Obsid    Plot
=====================  =====================  ==================  =============  =======  ===================
{% for viol in viols %}
{% if viol.type == "ACIS-S" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}             {{"%2.2f"|format(viol.duration)}}           {{viol.obsid}}        `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  =======  ===================
{% endif %}

ACIS-S Hot Violations
=====================

{% if num_viols.ACIS_H == 0 %}
No ACIS-S hot limit violations during this period.
{% else %}
=====================  =====================  ==================  =============  =======  ===================
Date start             Date stop              Max temperature     Duration (ks)  Obsid    Plot
=====================  =====================  ==================  =============  =======  ===================
{% for viol in viols %}
{% if viol.type == "ACIS-H" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}             {{"%2.2f"|format(viol.duration)}}           {{viol.obsid}}        `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================
=============  =======  ===================
{% endif %}

FPTEMP_11 Planning High Limit Violations
=============================================

{% if num_viols.Planning_hi == 0 %}
No planning high limit violations during this period.
{% else %}
=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Planning_hi" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%2.2f"|format(viol.maxtemp)}}              {{"%3.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================
{% endif %}

FPTEMP_11 Yellow High Limit Violations
=============================================

{% if num_viols.Yellow_hi == 0 %}
No yellow high limit violations during this period.
{% else %}
=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Yellow_hi" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%2.2f"|format(viol.maxtemp)}}              {{"%3.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================
{% endif %}

Violation Trends
================

{% if viols|length > 0 %}
.. image:: ../../_static/hist_{{msid.lower()}}_{{year}}.png
{% else %}
No violations in this period available for plotting.
{% endif %}

This page was last updated at {{last_update}}.
