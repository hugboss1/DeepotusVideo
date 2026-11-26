# GoatCounter (mesure d'audience sans cookie, EUPL-1.2) : binaire officiel de la version publiée, empreinte vérifiée.
# Mettre à jour : changer VERSION et SHA256 (gh release download vX -R arp242/goatcounter, puis sha256sum).
FROM alpine:3.21
ARG VERSION=v2.7.0
ARG SHA256=98d221cb9c8ef2bf76d8daa9cca647839f8d8b0bb5bc7400ff9337c5da834511
RUN apk add --no-cache ca-certificates \
 && wget -qO /tmp/gc.gz "https://github.com/arp242/goatcounter/releases/download/${VERSION}/goatcounter-${VERSION}-linux-amd64.gz" \
 && echo "${SHA256}  /tmp/gc.gz" | sha256sum -c - \
 && gunzip -c /tmp/gc.gz > /usr/local/bin/goatcounter && chmod 755 /usr/local/bin/goatcounter && rm /tmp/gc.gz
ENTRYPOINT ["/usr/local/bin/goatcounter"]
