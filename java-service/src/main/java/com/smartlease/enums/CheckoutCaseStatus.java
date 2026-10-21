package com.smartlease.enums;

public enum CheckoutCaseStatus {
    APPLYING, AWAITING_CONFIRM, COMPLETED, CANCELLED;

    public boolean active() {
        return this == APPLYING || this == AWAITING_CONFIRM;
    }
}