# Requirement: Data Sanitizer Idempotency
clean_user_input must sanitize dangerous HTML characters.
The sanitization operation must be idempotent (clean_user_input(clean_user_input(x)) == clean_user_input(x)).
