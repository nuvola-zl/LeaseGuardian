package com.smartlease.common.result;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.smartlease.common.code.ErrorCode;
import lombok.Data;

import java.io.Serializable;

/**
 * 统一返回结果。
 * @param <T> 业务数据类型
 */
@Data
public class Result<T> implements Serializable {

    public static final String SUCCESS = ErrorCode.SUCCESS;

    private String code;
    private String msg;
    private T data;
    private String requestId;

    public static <T> Result<T> success() {
        Result<T> result = new Result<>();
        result.code = SUCCESS;
        result.msg = "success";
        return result;
    }

    public static <T> Result<T> success(T data) {
        Result<T> result = success();
        result.data = data;
        return result;
    }

    public static <T> Result<T> error(String code, String msg) {
        Result<T> result = new Result<>();
        result.code = code;
        result.msg = msg;
        return result;
    }





    @JsonIgnore
    public boolean isSuccess() {
        return SUCCESS.equals(this.code);
    }

    @JsonIgnore
    public boolean isError() {
        return !isSuccess();
    }
}