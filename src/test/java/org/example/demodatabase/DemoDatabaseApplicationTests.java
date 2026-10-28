package org.example.demodatabase;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

// По умолчанию Spring Boot не запускает docker compose в тестах; здесь тест идёт в Postgres стенда
@SpringBootTest(properties = "spring.docker.compose.skip.in-tests=false")
class DemoDatabaseApplicationTests {

    @Test
    void contextLoads() {
    }

}
