ACIS-I -114 :math:`^\circ`C Violations
--------------------------------------

=====  =====================  =====================  ==================  ===================
Obsid  Date start             Date stop              Max temperature     Plot
=====  =====================  =====================  ==================  ===================
{% for viol in viols %}
{% if viol.instrument == "ACIS-I" %}
{{viol.obsid}}  {{viol.datestart}}  {{viol.datestop}}  {{"%.2f"|format(viol.maxtemp)}}             `link <{{viol.plot}}>`_
{% endif %}
{% endfor %}
=====  =====================  =====================  ==================  ===================


ACIS-S -112 :math:`^\circ`C Violations
--------------------------------------

=====  =====================  =====================  ==================  ===================
Obsid  Date start             Date stop              Max temperature     Plot
=====  =====================  =====================  ==================  ===================
{% for viol in viols %}
{% if viol.instrument == "ACIS-S" %}
{{viol.obsid}}  {{viol.datestart}}  {{viol.datestop}}  {{"%.2f"|format(viol.maxtemp)}}             `link <{{viol.plot}}>`_
{% endif %}
{% endfor %}
=====  =====================  =====================  ==================  ===================
