{{year}} Focal Plane Temperature Violations
-------------------------------------------

ACIS-I -114 C Violations
========================

=====================  =====================  ==================  =============  =======  ===================
Date start             Date stop              Max temperature     Duration (ks)  Obsid    Plot
=====================  =====================  ==================  =============  =======  ===================
{% for viol in viols %}
{% if viol.type == "ACIS-I" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}             {{"%2.2f"|format(viol.duration)}}           {{viol.obsid}}        `link <{{viol.plot}}>`_
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  =======  ===================


ACIS-S -112 C Violations
========================

=====================  =====================  ==================  =============  =======  ===================
Date start             Date stop              Max temperature     Duration (ks)  Obsid    Plot
=====================  =====================  ==================  =============  =======  ===================
{% for viol in viols %}
{% if viol.type == "ACIS-S" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}             {{"%2.2f"|format(viol.duration)}}           {{viol.obsid}}        `link <{{viol.plot}}>`_
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  =======  ===================

{% if viols|length > 0 %}
.. image:: ../_static/hist_{{msid.lower()}}_{{year}}.png
{% endif %}
