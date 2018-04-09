{{year}} {{msid}} Violations
----------------------------

=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"%.2f"|format(viol.maxtemp)}}               {{"%.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`_
{% endfor %}
=====================  =====================  ==================  =============  ===================

{% if viols|length > 0 %}
.. image:: ../_static/hist_{{msid}}_{{year}}.png
{% endif %}