#!/bin/bash

# Function to format config variable name (lowercase and replace underscore with dot)
format_config_name() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | tr '_' '.'
}

# Function to read .env file and set configs
set_configs() {
    echo "Setting Firebase config variables from .env..."
    config_pairs=""
    
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        
        # Remove any quotes from the value
        value=$(echo "$value" | sed -e 's/^["\x27]//' -e 's/["\x27]$//')
        
        # Skip secrets and ENVIRONMENT variable (secrets are handled separately and ENVIRONMENT is ignored)
        if [[ "$key" == *"_KEY"* ]] || [[ "$key" == "ENVIRONMENT" ]]; then
            continue
        fi
        
        # Format the key (lowercase and replace underscore with dot)
        formatted_key=$(format_config_name "$key")
        
        # Build config string
        if [[ -n "$config_pairs" ]]; then
            config_pairs+=" "
        fi
        config_pairs+="$formatted_key=\"$value\""
    done < .env
    
    # Set all configs at once
    if [[ -n "$config_pairs" ]]; then
        echo "Setting Firebase config variables..."
        echo "firebase functions:config:set $config_pairs"
        echo ""
        eval "firebase functions:config:set $config_pairs"
    fi
}

# Function to check and set secrets if different
set_secrets() {
    echo "Checking and setting Firebase secrets from .env..."
    
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        
        # Only process secret keys
        if [[ "$key" == *"_KEY"* ]]; then
            # Remove any quotes from the value
            value=$(echo "$value" | sed -e 's/^["\x27]//' -e 's/["\x27]$//')
            
            # Get current secret value
            current_secret=$(firebase functions:secrets:get "$key" 2>/dev/null)
            
            # If secret doesn't exist or is different, set it
            if [[ -z "$current_secret" || "$current_secret" != "$value" ]]; then
                echo "Setting secret: $key"
                echo "$value" | firebase functions:secrets:set "$key"
            else
                echo "Secret $key is already up to date"
            fi
        fi
    done < .env
}

# Main execution
if [[ ! -f .env ]]; then
    echo "Error: .env file not found!"
    exit 1
fi

# Set configs
set_configs

# Set secrets
set_secrets

echo "Done!"
echo "Please verify your settings using 'firebase functions:config:get' for config variables or 'firebase functions:secrets:get' for secrets" 
