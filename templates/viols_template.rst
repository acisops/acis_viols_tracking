{{year}} {{msid}} Violations
----------------------------

{{msid}} Planning Limit Violations
==================================

=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Planning" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}               {{"%.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`_
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================

{{msid}} Yellow Limit Violations
================================

=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Yellow" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}               {{"%.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`_
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================

{% if viols|length > 0 %}
.. image:: ../_static/hist_{{msid}}_{{year}}.png
{% endif %}