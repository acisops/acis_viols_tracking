{{year}} {{msid}} Violations

=====  =====================  =====================  ==================  ===================
Obsid  Date start             Date stop              Max temperature     Plot
=====  =====================  =====================  ==================  ===================
{% for viol in viols %}
{{viol.obsid}}  {{viol.datestart}}  {{viol.datestop}}  {{"%.2f"|format(viol.maxtemp)}}             `link <{{viol.plot}}>`_
{% endfor %}
=====  =====================  =====================  ==================  ===================
