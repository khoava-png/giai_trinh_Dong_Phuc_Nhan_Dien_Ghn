#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock dashboard_sync module for Cloud Run deployment when external file is absent.
"""
def _build_raw(cached_data):
    return str(cached_data)

def _deploy_to_cloudflare(raw_data):
    return "CF-MOCK-DEPLOY-ID"
