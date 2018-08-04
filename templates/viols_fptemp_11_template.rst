{{year}} Focal Plane Temperature Violations
-------------------------------------------

ACIS-I -114 C Violations
========================

{% if num_viols.ACIS-I == 0 %}
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

ACIS-S -112 C Violations
========================

{% if num_viols.ACIS-S == 0 %}
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

Violation Trends
================

{% if viols|length > 0 %}
.. image:: ../_static/hist_{{msid.lower()}}_{{year}}.png
{% else %}
No violations in this period available for plotting.
{% endif %}
