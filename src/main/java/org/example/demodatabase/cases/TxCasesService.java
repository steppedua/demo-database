package org.example.demodatabase.cases;

import lombok.RequiredArgsConstructor;
import org.example.demodatabase.account.AccountRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;

/**
 * Весь кейс: медленная работа внутри транзакции и она же до транзакции.
 * База свободна, а сервис лежит: кончаются соединения пула.
 */
@Service
@RequiredArgsConstructor
public class TxCasesService {

    private static final int ACCOUNT_ID = 1;
    private static final int AMOUNT = 1;
    private static final Duration SLOW_WORK = Duration.ofSeconds(20);

    private final AccountRepository accountRepository;

    /**
     * Проблема: медленная работа внутри транзакции — всё это время соединение занято.
     */
    @Transactional
    public void withdrawSlow() throws InterruptedException {
        accountRepository.findById(ACCOUNT_ID);           // BEGIN + SELECT: соединение взято из пула
        slowWork();                                       // ← соединение простаивает: idle in transaction
        accountRepository.withdraw(ACCOUNT_ID, AMOUNT);   // UPDATE + COMMIT: соединение вернулось в пул
    }

    /**
     * Исправление: сначала медленная работа, потом короткая транзакция.
     */
    public void withdrawSlowFixed() throws InterruptedException {
        slowWork();                                       // ← соединение ещё не взято
        accountRepository.withdraw(ACCOUNT_ID, AMOUNT);   // BEGIN + UPDATE + COMMIT — миллисекунды
    }

    /**
     * Изображает HTTP-вызов, рендер PDF, kafkaTemplate.send().get(): пулу всё равно, чем занят поток.
     */
    private static void slowWork() throws InterruptedException {
        Thread.sleep(SLOW_WORK);
    }
}
