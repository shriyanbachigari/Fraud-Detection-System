package com.frauddetection.service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;

@Service
public class VelocityService {
    
    private final StringRedisTemplate redis;
    
    public VelocityService(StringRedisTemplate redis) {
        this.redis = redis;
    }
    
    public boolean isDuplicate(String txnId) {
        String key = "dup:" + txnId;
        Boolean set = redis.opsForValue().setIfAbsent(key, "1", Duration.ofMinutes(10));
        return Boolean.FALSE.equals(set);
    }
    
    public int incrementVelocity(String userId) {
        String key = "vel:" + userId;
        Long count = redis.opsForValue().increment(key);
        redis.expire(key, Duration.ofSeconds(60));
        return count == null ? 0 : count.intValue();
    }
    
    public boolean isNewCountry(String userId, String country) {
        String key = "geo:" + userId;
        Long added = redis.opsForSet().add(key, country);
        redis.expire(key, Duration.ofHours(24));
        return added != null && added > 0;
    }
    
    public boolean isNewDevice(String userId, String device) {
        String key = "dev:" + userId;
        Long added = redis.opsForSet().add(key, device);
        redis.expire(key, Duration.ofHours(24));
        return added != null && added > 0;
    }
}
