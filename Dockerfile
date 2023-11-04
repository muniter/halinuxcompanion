FROM homeassistant/home-assistant:stable

COPY tests/entrypoint.sh /custom-entrypoint.sh
RUN chmod +x /custom-entrypoint.sh
RUN sed -i '5i\ sh /custom-entrypoint.sh' /init

ENTRYPOINT ["/init"]
