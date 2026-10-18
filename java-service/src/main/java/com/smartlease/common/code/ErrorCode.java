package com.smartlease.common.code;

/**
 * 错误码规范：A-BB-CCC
 * A：错误大类，A=业务/通用，B=系统，C=第三方
 * BB：业务域，00=通用，01=工单，02=租约，03=账单/支付，04=账号
 * CCC：域内具体错误
 */
public final class ErrorCode {



    private ErrorCode() {
    }

    // ========== 成功 ==========
    public static final String SUCCESS = "A00000";

    // ========== 通用域 A00 ==========
    public static final String PARAM_ERROR = "A00001";
    public static final String RESOURCE_NOT_FOUND = "A00002";
    public static final String RESOURCE_DUPLICATE = "A00003";
    public static final String RESOURCE_STATUS_INVALID = "A00004";
    public static final String SYSTEM_BUSY = "A00005";
    public static final String REQUEST_PROCESSED = "A00007";
    public static final String REMOTE_CALL_ERROR = "A00008";
    public static final String UNAUTHORIZED = "A00010";
    public static final String FORBIDDEN = "A00011";

    // ========== 工单域 A01 ==========
    public static final String TICKET_NOT_FOUND = "A01002";
    public static final String TICKET_DUPLICATE = "A01003";
    public static final String TICKET_STATUS_INVALID = "A01004";

    // ========== 租约域 A02 ==========
    // public static final String LEASE_NOT_FOUND = "A02002";
    // ========== 租约域 A02 ==========
    public static final String LEASE_NOT_FOUND = "A02002";
    public static final String LEASE_STATUS_INVALID = "A02004";
    public static final String CHECKOUT_MOVE_OUT_DATE_INVALID = "A02010";
    public static final String CHECKOUT_SETTLEMENT_VERSION_MISMATCH = "A02011";
    public static final String CHECKOUT_PENDING_DAMAGE = "A02012";
    public static final String CHECKOUT_BILL_BASIS_MISSING = "A02013";

    // ========== 预留：账单/支付域 A03 ==========
    // public static final String BILL_NOT_FOUND = "A03002";

    // ========== 账号域 A04 ==========
    /** 房间号格式非法：必须 3 位纯数字 */
    public static final String ROOM_NO_INVALID = "A04001";
    /** 用户名已存在 */
    public static final String USERNAME_EXISTS = "A04003";
    /** 房间已有人入住（存在生效/退租中的租约） */
    public static final String ROOM_OCCUPIED = "A04004";
    /** 用户名或密码错误（统一报错，不区分用户不存在/密码错，防账号枚举） */
    public static final String LOGIN_FAILED = "A04005";

    // ========== 系统错误 B00 ==========
    public static final String SYSTEM_ERROR = "B00001";
    public static final String DB_ERROR = "B00002";

    // ========== 第三方错误 C01：LLM/模型服务 ==========
    public static final String LLM_CALL_FAILED = "C01001";
    public static final String LLM_TIMEOUT = "C01002";
}