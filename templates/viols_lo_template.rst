{{year}} {{msid}} Low Violations
------------------------------------------

{{msid}} Planning Low Limit Violations
==============================================

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

{{msid}} Yellow Low Limit Violations
==============================================

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


Low Violation Trends
====================

{% if num_viols.Yellow_lo > 0 or num_viols.Planning_lo > 0 %}
.. image:: ../../_static/hist_{{msid.lower()}}_{{year}}_lo.png
{% else %}
No violations in this period available for plotting.
{% endif %}

This page was last updated at {{last_update}}.