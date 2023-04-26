#!/bin/bash

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
