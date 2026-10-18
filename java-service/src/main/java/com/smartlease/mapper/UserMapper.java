package com.smartlease.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import com.smartlease.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
@Mapper
public interface UserMapper extends BaseMapper<User> {

    /**
     * 撞房校验: 该房间是否已有"生效 (ACTIVE) 或退租中 (TERMINATING)" 的租约
     *
     * 应用层预检, 保证注册时给出友好报错 (A04004);
     * 数据库层兜底由 lease.uk_tenant_active 唯一索引保证"一人一张生效租约",
     * 万一并发绕过预检, DuplicateKeyException 由 GlobalExceptionHandler 统一兜成 409。
     */
    @Select("SELECT COUNT(1) FROM `user` u JOIN lease l ON l.tenant_id = u.id "
            + "WHERE u.room_no = #{roomNo} AND l.status IN ('ACTIVE', 'TERMINATING')")
    long countOccupiedByRoomNo(@Param("roomNo") String roomNo);
}
