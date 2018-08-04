{{year}} {{msid}} Violations
----------------------------

{{msid}} Planning Limit Violations
==================================

{% if num_viols.Planning == 0 %}
No planning limit violations during this period. 
{% else %}
=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Planning" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}               {{"%.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================
{% endif %}

{{msid}} Yellow Limit Violations
================================

{% if num_viols.Yellow == 0 %}
No yellow limit violations during this period. 
{% else %}
=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Yellow" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}               {{"%.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================
{% endif %}

Violation Trends
================

{% if viols|length > 0 %}
.. image:: ../_static/hist_{{msid.lower()}}_{{year}}.png
{% else %}
No violations in this period available for plotting.
{% endif %}
