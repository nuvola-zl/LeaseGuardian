package com.smartlease.common.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * JWT 配置, 对应 yml 的 leaseguardian.jwt 节点
 */
@Data
@Component
@ConfigurationProperties(prefix = "leaseguardian.jwt")
public class JwtProperties {

    /** Base64 编码的密钥 (至少 256 bit, 建议 openssl rand -base64 64 生成) */
    private String secretKey;

    /** token 有效期, 单位: 小时 */
    private long ttlHours = 24;
}
