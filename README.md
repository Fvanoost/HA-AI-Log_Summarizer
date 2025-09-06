# HA-AI-Log_Summarizer
This code use AppDaemon to push logs to Gemini and get a "AI" summary of potential issues/improvement. This is my first repository (be kind) and would love to get your view. The code is based on the amazing work done from @toxicstarknova (cf reddit link : https://www.reddit.com/r/homeassistant/comments/1lxcdsm/ai_log_analysis_tool_install_instructions/). As I have a HA Yellow, some of the code didn't work well out of the box and I had to tweak it until it works (ie AppDaemon API call work in a different way on Yellow)

## Pre Requisites :  
    1. AppDaemon addons needs to be installed  
    2. sensor.uptime to be made available using uptime integration  
    3. Beware that HA Yellow handle AppDaemon in a specific way  
        - the path of the config file is NOT in /config or /homeassistant but is AAXXCCDD_APPDAEMON (replace AAXXCCDD with whatever your hostname is in the addon ). Therefor your apps.yaml will need to be stored under a directory apps under AAXXCCDD_APPDAEMON and your appdaemon.yaml under AAXXCCDD_APPDAEMON
    4. extra sensors to be created  
```yaml
    
  - name: "ha_device_count"
    state: >
        {{ states | map(attribute='entity_id') | map('device_id') | unique | list | length }}
  - name: "ha_entity_count"
    state: "{{ states | count }}"
  - name: "ha_entity_unavailable_count"
    unique_id: ha_entity_unavailable_count
    state: >
      {{ states
        | selectattr('state', 'in', ['unavailable', 'unknown'])
        | list
        | count }}
    attributes:
      unavailable_entities: >
        {{ states
          | selectattr('state', 'in', ['unavailable', 'unknown'])
          | map(attribute='entity_id')
          | list }}
  - name: "Home Assistant Uptime"
    state: >-
      {% set last_start = as_datetime(states('sensor.uptime')) %}
      {% set delta = now() - last_start %}
      {% set days = delta.days %}
      {% set hours = (delta.seconds // 3600) %}
      {% set minutes = (delta.seconds % 3600) // 60 %}
      {% set seconds = delta.seconds % 60 %}
      {% if days > 0 %}
        {{ days }}d {{ hours }}h {{ minutes }}m
      {% elif hours > 0 %}
        {{ hours }}h {{ minutes }}m {{ seconds }}s
      {% elif minutes > 0 %}
        {{ minutes }}m {{ seconds }}s
      {% else %}
        {{ seconds }}s
      {% endif %}
    icon: mdi:clock-outline
```
    5. apps.yaml to include
```yaml
log_summarizer:
  module: log_summarizer_app
  class: LogSummarizer
  api_key: !secret google_api_key
  notification_target: notify.persistent_notification
  gemini_api_key: !secret gemini_api_key
  ha_url: http://homeassistant.local:8123
  ha_token: !secret ha_long_lived_token 
  ```

