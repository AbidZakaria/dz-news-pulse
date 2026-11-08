{#
  By default dbt prefixes custom schemas with the target schema (analytics_marts ...).
  We want the exact names instead: staging / intermediate / marts / reference.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
