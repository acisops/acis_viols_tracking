{{year}} {{msid}} High Violations
--------------------------------------------

{{msid}} Planning High Limit Violations
=============================================

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

{{msid}} Yellow High Limit Violations
=============================================

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

High Violation Trends
=====================

{% if num_viols.Yellow_hi > 0 or num_viols.Planning_hi > 0 %}
.. image:: ../../_static/hist_{{msid.lower()}}_{{year}}_hi.png
{% else %}
No violations in this period available for plotting.
{% endif %}

This page was last updated at {{last_update}}.