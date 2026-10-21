package com.smartlease.enums;

/**
 * 工单状态枚举。
 * 数据库存英文码，中文只用于展示/文档。
 */
public enum RepairTicketStatus {
    REGISTERED,
    PROCESSING,
    DONE,
    CANCELLED;

    public boolean canTransitionTo(RepairTicketStatus target) {
        if (target == null) {
            return false;
        }
        return switch (this) {
            case REGISTERED -> target == PROCESSING || target == CANCELLED;
            case PROCESSING -> target == DONE || target == CANCELLED;
            case DONE, CANCELLED -> false;
        };
    }
}