package com.smartlease.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import com.smartlease.entity.Lease;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface LeaseMapper extends BaseMapper<Lease> {
}
