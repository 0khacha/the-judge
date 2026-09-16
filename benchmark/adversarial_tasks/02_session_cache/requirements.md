# Requirement: Session Store Expiration
SessionStore must store and fetch session payloads.
Sessions requested after window_seconds has elapsed must expire and return None.
