package com.smartlease.common.exception;

import com.smartlease.common.code.ErrorCode;
import com.smartlease.common.result.Result;
import jakarta.validation.ConstraintViolationException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.UUID;

/**
 * 全局异常处理：controller 不捕获异常，统一在这里转 Result。
 *
 * 本次新增 (账号域接入):
 * 1. handleValidation: @RequestBody 的 @NotBlank 等校验失败出口,
 *    缺少它时参数错误会掉进 handleUnknown 变成 500 "系统繁忙";
 * 2. handleConstraintViolation: @PathVariable / 查询参数的校验失败出口 (预留)。
 * 原有 handler 一行未动。
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    private String requestId() {
        return UUID.randomUUID().toString().substring(0, 8);
    }

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Result<Object>> handleBusinessException(BusinessException e) {
        String requestId = requestId();
        log.warn("业务异常 | requestId={} | code={} | msg={}", requestId, e.getCode(), e.getMessage());

        Result<Object> result = Result.error(e.getCode(), e.getMessage());
        result.setRequestId(requestId);

        return ResponseEntity.status(e.getHttpStatus()).body(result);
    }

    /** 新增: @RequestBody 参数校验失败 (@NotBlank 等) */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Result<Object>> handleValidation(MethodArgumentNotValidException e) {
        String requestId = requestId();
        String msg = e.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(FieldError::getDefaultMessage)
                .orElse("参数校验失败");
        log.warn("参数校验失败 | requestId={} | msg={}", requestId, msg);
        Result<Object> result = Result.error(ErrorCode.PARAM_ERROR, msg);
        result.setRequestId(requestId);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(result);
    }

    /** 新增: @PathVariable / 查询参数校验失败出口 (预留) */
    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<Result<Object>> handleConstraintViolation(ConstraintViolationException e) {
        String requestId = requestId();
        String msg = e.getConstraintViolations().stream()
                .findFirst()
                .map(v -> v.getMessage())
                .orElse("参数校验失败");
        log.warn("参数校验失败 | requestId={} | msg={}", requestId, msg);
        Result<Object> result = Result.error(ErrorCode.PARAM_ERROR, msg);
        result.setRequestId(requestId);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(result);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Result<Object>> handleNotReadable(HttpMessageNotReadableException e) {
        String requestId = requestId();
        log.warn("请求体不是合法JSON | requestId={} | msg={}", requestId, e.getMessage());
        Result<Object> result = Result.error(ErrorCode.PARAM_ERROR, "请求数据格式错误，请检查JSON参数");
        result.setRequestId(requestId);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(result);
    }

    @ExceptionHandler(DuplicateKeyException.class)
    public ResponseEntity<Result<Object>> handleDuplicateKey(DuplicateKeyException e) {
        String requestId = requestId();
        log.warn("唯一索引冲突 | requestId={} | msg={}", requestId, e.getMessage());
        Result<Object> result = Result.error(ErrorCode.RESOURCE_DUPLICATE, "资源已存在或请求重复");
        result.setRequestId(requestId);
        return ResponseEntity.status(HttpStatus.CONFLICT).body(result);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Result<Object>> handleUnknown(Exception e) {
        String requestId = requestId();
        log.error("未知系统异常 | requestId={}", requestId, e);
        Result<Object> result = Result.error(ErrorCode.SYSTEM_ERROR, "系统繁忙，请稍后再试");
        result.setRequestId(requestId);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(result);
    }
}
