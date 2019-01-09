{{year}} {{msid}} Violations
--------------------------------

{{msid}} Planning Limit Violations
========================================

Planning High Limit
+++++++++++++++++++

{% if num_viols.Planning_hi == 0 %}
No planning high limit violations during this period. 
{% else %}
=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Planning_hi" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"% 2.2f"|format(viol.maxtemp)}}               {{"% 3.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================
{% endif %}

Planning Low Limit
++++++++++++++++++

{% if num_viols.Planning_lo == 0 %}
No planning low limit violations during this period. 
{% else %}
=====================  =====================  ==================  =============  ===================
Date start             Date stop              Min temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Planning_lo" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"% 2.2f"|format(viol.mintemp)}}               {{"% 3.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================
{% endif %}

{{msid}} Yellow Limit Violations
======================================

Yellow High Limit
+++++++++++++++++

{% if num_viols.Yellow_hi == 0 %}
No yellow high limit violations during this period. 
{% else %}
=====================  =====================  ==================  =============  ===================
Date start             Date stop              Max temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Yellow_hi" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"% 2.2f"|format(viol.maxtemp)}}               {{"% 3.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`__
{% endif %}
{% endfor %}
=====================  =====================  ==================  =============  ===================
{% endif %}

Yellow Low Limit
++++++++++++++++

{% if num_viols.Yellow_lo == 0 %}
No yellow low limit violations during this period. 
{% else %}
=====================  =====================  ==================  =============  ===================
Date start             Date stop              Min temperature     Duration (ks)  Plot
=====================  =====================  ==================  =============  ===================
{% for viol in viols %}
{% if viol.type == "Yellow_lo" %}
{{viol.viol_datestart}}  {{viol.viol_datestop}}  {{"% 2.2f"|format(viol.mintemp)}}               {{"% 3.2f"|format(viol.duration)}}           `link <{{viol.plot}}>`__
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
