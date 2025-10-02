package com.frauddetection.web;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

@RestController
@RequestMapping("/alerts")
public class AlertStreamController {

    private final JdbcTemplate jdbc;

    public AlertStreamController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping(path = "/stream")
    public SseEmitter stream() {
        // No timeout to keep stream open
        final SseEmitter emitter = new SseEmitter(0L);
        final AtomicBoolean closed = new AtomicBoolean(false);

        Long initial = jdbc.queryForObject("SELECT COALESCE(MAX(id),0) FROM flags", Long.class);
        final AtomicLong lastId = new AtomicLong(initial == null ? 0L : initial);

        ScheduledExecutorService exec = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "alerts-sse");
            t.setDaemon(true);
            return t;
        });

        ScheduledFuture<?> task = exec.scheduleAtFixedRate(() -> {
            if (closed.get()) return;
            try {
                List<Map<String, Object>> rows = jdbc.queryForList(
                        "SELECT id, txn_id, score, reasons_json, timestamp FROM flags WHERE id > ? ORDER BY id ASC",
                        lastId.get()
                );
                for (Map<String, Object> row : rows) {
                    Number id = (Number) row.get("id");
                    if (id != null) {
                        lastId.set(id.longValue());
                    }
                    emitter.send(row);
                }
            } catch (Exception e) {
                emitter.completeWithError(e);
                closed.set(true);
            }
        }, 0, 1, TimeUnit.SECONDS);

        Runnable cleanup = () -> {
            closed.set(true);
            task.cancel(true);
            exec.shutdownNow();
        };
        emitter.onCompletion(cleanup);
        emitter.onTimeout(cleanup);

        return emitter;
    }
}
