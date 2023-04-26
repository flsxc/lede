#!/bin/bash

# List of blocked domains
BLOCKED_DOMAINS=("youtube.com" "facebook.com" "twitter.com")

if [ ! -f /etc/iptables.rules ]; then
  # Add iptables rules for each blocked domain
  for domain in "${BLOCKED_DOMAINS[@]}"; do
    iptables -A OUTPUT -m string --string "${domain}" --algo bm --to 65535 -j DROP
  done

  # Save the current iptables rules
  iptables-save > /etc/iptables.rules

  # Create the iptables startup script
  cat > /etc/network/if-pre-up.d/iptables << EOF
#!/bin/sh
/sbin/iptables-restore < /etc/iptables.rules
EOF

  # Set the executable permission for the startup script
  chmod +x /etc/network/if-pre-up.d/iptables

  echo "Iptables rules saved and startup script created successfully."
else
  echo "Iptables rules file already exists. Skipping rules creation."
fi
