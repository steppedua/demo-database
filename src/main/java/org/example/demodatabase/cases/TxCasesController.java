package org.example.demodatabase.cases;

import lombok.RequiredArgsConstructor;
import org.springframework.core.NestedExceptionUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Каждый эндпоинт — 40 одновременных клиентов на пул из 10 соединений.
 * Ответ приходит, когда закончат все: сколько прошло и с какой ошибкой упали остальные.
 */
@RestController
@RequestMapping("/cases")
@RequiredArgsConstructor
public class TxCasesController {

    private static final int CLIENTS = 40;

    private final TxCasesService cases;

    /**
     * Проблема. Через ~40 с: {"demo-pool - Connection is not available": 20, "ok": 20}
     */
    @PostMapping("/slow")
    public Map<String, Integer> slow() {
        return runClients(cases::withdrawSlow);
    }

    /**
     * Исправление. Через ~20 с: {"ok": 40}
     */
    @PostMapping("/slow/fixed")
    public Map<String, Integer> slowFixed() {
        return runClients(cases::withdrawSlowFixed);
    }

    /**
     * Запускает 40 клиентов одновременно и считает, чем закончился каждый.
     */
    private Map<String, Integer> runClients(Call call) {
        Map<String, Integer> results = new ConcurrentHashMap<>();
        try (ExecutorService clients = Executors.newFixedThreadPool(CLIENTS)) {
            for (int i = 0; i < CLIENTS; i++) {
                clients.submit(() -> results.merge(callOnce(call), 1, Integer::sum));
            }
        }   // выход из try ждёт, пока закончат все 40 клиентов
        return new TreeMap<>(results);
    }

    /**
     * Один клиент: "ok" или коротко — почему упал.
     */
    private static String callOnce(Call call) {
        try {
            call.run();
            return "ok";
        } catch (Exception e) {
            return shortReason(e);
        }
    }

    /**
     * "demo-pool - Connection is not available, request timed out after 30000ms (…)" → "demo-pool - Connection is not available"
     */
    private static String shortReason(Exception e) {
        String message = NestedExceptionUtils.getMostSpecificCause(e).getMessage();
        return String.valueOf(message).split(",")[0];
    }

    /**
     * Метод сервиса. throws Exception — потому что внутри Thread.sleep.
     */
    private interface Call {
        void run() throws Exception;
    }
}
