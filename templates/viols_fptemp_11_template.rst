{{year}} Focal Plane Temperature Violations
-------------------------------------------

ACIS-I -114 :math:`^\circ`C Violations
======================================

=====================  =====================  ==================  =============  =====  ===================
Date start             Date stop              Max temperature     Duration (ks)  Obsid  Plot
=====================  =====================  ==================  =============  =====  ===================
{% for viol in viols %}
{% if viol.type == "ACIS-I" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}                 {{"%.2f"|format(viol.duration)}}       {{viol.obsid}}        `link <{{viol.plot}}>`_
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  =====  ===================


ACIS-S -112 :math:`^\circ`C Violations
======================================

=====================  =====================  ==================  =============  =====  ===================
Date start             Date stop              Max temperature     Duration (ks)  Obsid  Plot
=====================  =====================  ==================  =============  =====  ===================
{% for viol in viols %}
{% if viol.type == "ACIS-S" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}                 {{"%.2f"|format(viol.duration)}}       {{viol.obsid}}        `link <{{viol.plot}}>`_
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  =====  ===================
