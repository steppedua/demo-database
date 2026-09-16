package org.example.demodatabase.account;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "acc")
@Getter
@Setter
@NoArgsConstructor
public class Account {

    @Id
    private Integer id;

    private Integer balance;
}
