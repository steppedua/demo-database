package org.example.demodatabase.account;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.transaction.annotation.Transactional;

public interface AccountRepository extends JpaRepository<Account, Integer> {

    /**
     * Списание одним UPDATE в своей короткой транзакции (или внутри внешней, если она уже открыта).
     */
    @Transactional
    @Modifying
    @Query("update Account a set a.balance = a.balance - :amount where a.id = :id")
    int withdraw(Integer id, int amount);
}
