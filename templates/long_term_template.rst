Long-Term Violation Trends
--------------------------

{% for msid in msids %}
{{msid.upper()}} Violations
===========================

.. image:: _static/hist_{{msid}}.png

{% endfor %}